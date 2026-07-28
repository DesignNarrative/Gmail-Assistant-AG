from typing import List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text, select, desc
from app.models.chat_message import ChatMessage
from app.models.conversation import Conversation
from app.models.document_chunk import DocumentChunk
from app.models.attachment import Attachment
from app.models.email import Email
from app.services.ai.embedding_service import generate_single_embedding
from app.core.config import get_settings
import logging
import json
from uuid import UUID

logger = logging.getLogger(__name__)
settings = get_settings()

GROQ_MODEL = settings.GROQ_MODEL
MAX_CONTEXT_CHUNKS = 15
MAX_CONTEXT_CHARS = 14000

SYSTEM_PROMPT = """You are an elite AI Executive Intelligence Assistant for the Director of Abhinav Group.

You work exactly like ChatGPT or Claude — but your knowledge is grounded in the Director's synced Gmail emails, PDFs, Excel files, contracts, HR correspondence, and corporate documents.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
OUTPUT FORMAT RULES (FOLLOW STRICTLY):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. CLEAN STRUCTURE — Organize every answer with clear sections using ## headings and ### sub-headings. Never dump raw text.

2. TABLES — Use proper Markdown table syntax for any comparison, list, pricing, or multi-column data:
   | Column A | Column B | Column C |
   |----------|----------|----------|
   | value    | value    | value    |
   ⚠️ NEVER put | pipe characters inside a table cell value. Use commas or semicolons instead.

3. CITATIONS — Cite sources ONCE per section or at the end of a paragraph. Do NOT repeat the full citation after every single bullet point.
   Format: > 📧 *"Email Subject"* — From: Name <email> — Date: DD Mon YYYY
   Or for attachments: > 📎 *filename.pdf / spreadsheet.xlsx*

4. CONCISE BUT COMPLETE — Be precise. Include all key facts (names, dates, numbers, terms) but do not pad or repeat information.

5. EXPERT ADVICE — Go beyond summarizing. Provide:
   • Legal interpretation and risk flags
   • Procurement/vendor analysis
   • HR and employment law perspective
   • Financial insights from spreadsheet data
   • Strategic recommendations

6. ANSWER EXACTLY WHAT IS ASKED — If asked to summarize one email, summarize that email. If asked for legal advice, give legal advice. Do not mix topics unless specifically requested.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STRICT RULES:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
• Only use facts, names, dates, and numbers present in the provided context.
• If a specific fact is not in the context, say "Not mentioned in available emails" — do not invent information.
• Never repeat the same citation more than once per section.
• Keep tables pipe-clean — no | characters inside cell values.
• Professional executive tone throughout.
"""


GENERAL_KNOWLEDGE_PROMPT = """You are an elite AI Executive Intelligence Assistant for the Director of Abhinav Group.

The director's question is general in nature, or could not be answered from the synced emails/documents. Answer using your own knowledge.

OUTPUT FORMAT (FOLLOW STRICTLY):
1. CLEAN STRUCTURE — Use ## headings and ### sub-headings. Never dump raw text.
2. TABLES — Use Markdown tables for any comparison or multi-column data:
   | Column A | Column B |
   |----------|----------|
   | value    | value    |
   ⚠️ NEVER put | pipe characters inside a table cell value — use commas instead.
3. CONCISE BUT COMPLETE — Include all key facts, numbers, and context.

RULES:
• Answer from your general knowledge. Do NOT fabricate email citations or source references.
• If you are uncertain or lack specific data, say so honestly rather than guessing.
• For legal, financial, tax, or HR matters, give general guidance and recommend consulting a qualified professional for the director's specific situation.
• Professional executive tone throughout.
"""

# Minimum cosine-similarity score for a retrieved chunk to count as "relevant".
# General-knowledge questions require a stronger match to be treated as email-grounded.
RELEVANCE_THRESHOLD = 0.40
GENERAL_QUESTION_RELEVANCE_THRESHOLD = 0.55

GENERAL_QUESTION_KEYWORDS = [
    "market salary", "salary for", "salary should", "salary range",
    "industry standard", "industry average", "market rate", "market trend",
    "legal definition", "what is the law", "according to law", "labour law",
    "best practice", "how do i", "how should", "what should i", "what should we",
    "recommend", "recommendation", "advise", "advice on",
    "average", "benchmark", "typical", "commonly", "generally",
    "explain what", "define ", "what is the difference",
    "current market", "going rate", "standard rate",
]


def _is_general_question(q_lower: str) -> bool:
    return any(kw in q_lower for kw in GENERAL_QUESTION_KEYWORDS)


# Phrases the email-grounded LLM uses when the synced emails/documents do NOT
# contain the answer. When one of these appears (in hybrid mode) we fall back to
# a general-knowledge answer. This is more reliable than the cosine threshold
# alone, because loosely-related emails can still score above the threshold.
INSUFFICIENT_ANSWER_MARKERS = [
    "not mentioned in available emails",
    "not mentioned in the available emails",
    "not mentioned",
    "no mention of",
    "do not mention",
    "does not mention",
    "do not provide",
    "does not provide",
    "do not provide any",
    "does not provide any",
    "none of these emails",
    "none of the emails",
    "do not specify",
    "does not specify",
    "not specified in",
    "no information about",
    "no information on",
    "no relevant information",
    "do not contain",
    "does not contain",
    "not provided in the",
    "could not find",
    "unable to find",
    "not available in the emails",
    "not found in the available",
]


def _answer_is_insufficient(answer: str) -> bool:
    if not answer:
        return True
    a_lower = answer.lower()
    return any(marker in a_lower for marker in INSUFFICIENT_ANSWER_MARKERS)


def _call_groq(system_prompt: str, user_message: str, temperature: float = 0.1):
    """Call Groq synchronously and return (answer, model_used)."""
    from groq import Groq
    client = Groq(api_key=settings.GROQ_API_KEY)
    response = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ],
        temperature=temperature,
        max_tokens=3000
    )
    return response.choices[0].message.content.strip(), GROQ_MODEL


async def _stream_groq(system_prompt: str, user_message: str, temperature: float = 0.1):
    """Call Groq with streaming enabled; yield answer text deltas as they arrive."""
    from groq import AsyncGroq
    client = AsyncGroq(api_key=settings.GROQ_API_KEY)
    stream = await client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ],
        temperature=temperature,
        max_tokens=3000,
        stream=True
    )
    async for chunk in stream:
        if chunk.choices and chunk.choices[0].delta and chunk.choices[0].delta.content:
            yield chunk.choices[0].delta.content


def _sse(payload: Dict[str, Any]) -> str:
    """Format a payload as a Server-Sent Events data frame."""
    return f"data: {json.dumps(payload)}\n\n"


async def retrieve_relevant_chunks(
    question: str,
    db: AsyncSession,
    user_id: UUID,
    top_k: int = MAX_CONTEXT_CHUNKS
) -> List[Dict[str, Any]]:
    """
    Embed the question and find the most similar document chunks belonging to the user using cosine similarity via pgvector.
    """
    question_embedding = generate_single_embedding(question)
    if not question_embedding:
        logger.warning("Failed to generate question embedding")
        return []

    embedding_str = "[" + ",".join(str(x) for x in question_embedding) + "]"

    sql = text("""
        SELECT 
            dc.id,
            dc.chunk_text,
            dc.attachment_id,
            dc.email_id,
            dc.processed_doc_id,
            COALESCE(a.filename, e.subject, 'Email Content') AS filename,
            e.subject AS email_subject,
            e.sender_name AS sender_name,
            e.sender_email AS sender_email,
            e.date_sent AS date_sent,
            1 - (dc.embedding <=> CAST(:query_vec AS vector)) AS similarity_score
        FROM document_chunks dc
        LEFT JOIN attachments a ON a.id = dc.attachment_id
        LEFT JOIN emails e ON e.id = dc.email_id
        WHERE dc.embedding IS NOT NULL AND dc.user_id = :user_id
        ORDER BY dc.embedding <=> CAST(:query_vec AS vector)
        LIMIT :top_k
    """)

    result = await db.execute(sql, {"query_vec": embedding_str, "user_id": user_id, "top_k": top_k})
    rows = result.fetchall()

    chunks = []
    for row in rows:
        chunks.append({
            "chunk_id": str(row.id),
            "chunk_text": row.chunk_text,
            "attachment_id": str(row.attachment_id) if row.attachment_id else None,
            "email_id": str(row.email_id) if row.email_id else None,
            "processed_doc_id": str(row.processed_doc_id) if row.processed_doc_id else None,
            "filename": row.filename,
            "subject": row.email_subject,
            "sender_name": row.sender_name,
            "sender_email": row.sender_email,
            "date_sent": row.date_sent.isoformat() if row.date_sent else None,
            "similarity_score": float(row.similarity_score)
        })

    logger.info(f"Retrieved {len(chunks)} relevant chunks for user {user_id}: '{question[:80]}'")
    return chunks


async def fetch_full_email_catalog(db: AsyncSession, user_id: UUID) -> str:
    """
    Build a comprehensive catalog of ALL synced emails belonging to the user with full bodies and attachment info.
    """
    stmt = select(Email).where(Email.user_id == user_id).order_by(desc(Email.date_sent))
    emails = (await db.execute(stmt)).scalars().all()

    if not emails:
        return "No emails found in the database."

    lines = ["═══ COMPLETE EMAIL CATALOG (Director's AI Assistant Label) ═══\n"]

    for i, e in enumerate(emails, 1):
        att_stmt = select(Attachment).where(Attachment.email_id == e.id)
        atts = (await db.execute(att_stmt)).scalars().all()
        att_names = ", ".join([f"{a.filename} ({a.mime_type})" for a in atts]) if atts else "None"

        body = e.body_text or e.snippet or "(No body content)"
        # Include full body up to 1500 chars per email for broad summaries
        body_preview = body[:1500] + ("..." if len(body) > 1500 else "")

        lines.append(
            f"── EMAIL #{i} ──\n"
            f"Subject: {e.subject}\n"
            f"From: {e.sender_name or ''} <{e.sender_email}>\n"
            f"Date: {e.date_sent or e.date_received}\n"
            f"Attachments: {att_names}\n"
            f"Body:\n{body_preview}\n"
        )

    return "\n".join(lines)


async def _prepare_rag(
    question: str,
    db: AsyncSession,
    u_uuid: UUID,
    mode: str
) -> Dict[str, Any]:
    """
    Shared retrieval + prompt-building for the blocking and streaming RAG paths.

    Decides the knowledge source and returns:
      source_type   — no_emails | general_knowledge | email_grounded
      static_answer — pre-built answer when no LLM call is needed (else None)
      system_prompt / user_message / temperature — the LLM call to make
      used_chunks   — chunks included in the context (for citations)
    """
    # Count vector chunks for this user
    count_result = await db.execute(
        text("SELECT COUNT(*) FROM document_chunks WHERE embedding IS NOT NULL AND user_id = :user_id"),
        {"user_id": u_uuid}
    )
    chunk_count = count_result.scalar()

    q_lower = question.lower()

    # Broad summary queries — inject the full catalog
    is_broad_query = any(w in q_lower for w in [
        "summarize", "summary", "list email", "all email", "overview",
        "what email", "recent email", "inbox", "tell me about", "what do",
        "everything", "all the", "show me"
    ])
    is_general_question = _is_general_question(q_lower)

    # Retrieve chunks (if any exist) to assess relevance
    chunks: List[Dict[str, Any]] = []
    top_score = 0.0
    if chunk_count > 0:
        chunks = await retrieve_relevant_chunks(question, db, u_uuid)
        if chunks:
            top_score = chunks[0]["similarity_score"]

    # General questions require a stronger match to count as email-grounded
    threshold = GENERAL_QUESTION_RELEVANCE_THRESHOLD if is_general_question else RELEVANCE_THRESHOLD
    has_relevant_context = top_score >= threshold and len(chunks) > 0

    context_parts: List[str] = []
    used_chunks: List[Dict[str, Any]] = []

    if chunk_count == 0 and not (mode == "hybrid" and is_general_question):
        # No emails synced and not a general-knowledge question -> prompt to sync
        return {
            "source_type": "no_emails",
            "top_score": top_score,
            "static_answer": (
                "⚠️ **No emails or documents have been synced yet.**\n\n"
                "Please go to the **Dashboard** and click **'Sync Labeled Emails'** to import your Gmail data from the "
                "'Director's AI Assistant' label. Once synced, I can answer any question based on those emails and attachments."
            ),
            "system_prompt": None,
            "user_message": None,
            "temperature": 0.0,
            "used_chunks": [],
        }

    if mode == "hybrid" and not has_relevant_context:
        # Hybrid mode: no relevant email context -> answer from the LLM's general
        # knowledge, clearly flagged (no email citations).
        return {
            "source_type": "general_knowledge",
            "top_score": top_score,
            "static_answer": None,
            "system_prompt": GENERAL_KNOWLEDGE_PROMPT,
            "user_message": question,
            "temperature": 0.3,
            "used_chunks": [],
        }

    # Email-grounded strict RAG (email_only mode, or hybrid with relevant context)

    # Inject full email catalog for broad queries OR when chunks are low
    if is_broad_query or chunk_count < 5:
        email_catalog = await fetch_full_email_catalog(db, u_uuid)
        context_parts.append(email_catalog)

    # Add vector-retrieved chunks (most relevant content)
    total_chars = sum(len(cp) for cp in context_parts)
    for chunk in chunks:
        if total_chars + len(chunk["chunk_text"]) > MAX_CONTEXT_CHARS:
            break
        context_parts.append(
            f"[SOURCE: {chunk['filename']}]\n"
            f"{chunk['chunk_text']}"
        )
        total_chars += len(chunk["chunk_text"])
        used_chunks.append(chunk)

    if not context_parts:
        # Edge case: chunks existed but nothing gathered
        return {
            "source_type": "email_grounded",
            "top_score": top_score,
            "static_answer": "Not mentioned in available emails.",
            "system_prompt": None,
            "user_message": None,
            "temperature": 0.0,
            "used_chunks": [],
        }

    context_text = "\n\n---\n\n".join(context_parts)

    user_message = f"""CONTEXT — Director's synced Gmail emails and documents:

{context_text}

---

QUESTION: {question}

INSTRUCTIONS:
- Answer only what is asked. Do not add unrelated topics.
- Use ## headings, bullet points, and tables as appropriate.
- For tables: NEVER use pipe | characters inside cell values — use commas instead.
- Cite each email/document ONCE per section using: > 📧 "Subject" — From: Name — Date
- Do not repeat the same citation on every bullet point.
- Be concise and professional. Give expert analysis, not just a summary."""

    return {
        "source_type": "email_grounded",
        "top_score": top_score,
        "static_answer": None,
        "system_prompt": SYSTEM_PROMPT,
        "user_message": user_message,
        "temperature": 0.1,
        "used_chunks": used_chunks,
    }


def _error_answer(e: Exception) -> str:
    """User-friendly answer text for an AI-service failure."""
    err_str = str(e)
    if any(m in err_str.lower() for m in ["rate_limit", "429", "tokens per day", "rate limit"]):
        return (
            "⚠️ **Daily AI quota reached.**\n\n"
            "Today's Groq token limit has been used up. The limit refills gradually, so please "
            "try again in a little while — or upgrade the Groq plan for higher limits. "
            "Your emails and documents are safe; nothing was lost."
        )
    return f"⚠️ **AI Service Error**: {err_str}\n\nPlease try again shortly."


def _build_sources(source_type: str, used_chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Build source citations (only meaningful for email-grounded answers)."""
    if source_type != "email_grounded" or not used_chunks:
        return []
    return [
        {
            "filename": c["filename"],
            "chunk_text": c["chunk_text"][:300],
            "score": round(c["similarity_score"], 3),
            # Email metadata for richer citations (may be None for non-email chunks)
            "subject": c.get("subject"),
            "sender": c.get("sender_name") or c.get("sender_email"),
            "sender_email": c.get("sender_email"),
            "date": c.get("date_sent"),
        }
        for c in used_chunks
    ]


def _error_result(question: str, answer: str, conversation_id: str) -> Dict[str, Any]:
    """Transient-error response; NOT persisted to chat history."""
    from datetime import datetime, timezone
    return {
        "id": f"error-{datetime.now(timezone.utc).timestamp()}",
        "conversation_id": conversation_id,
        "question": question,
        "answer": answer,
        "sources": [],
        "model_used": None,
        "source_type": "error",
        "created_at": datetime.now(timezone.utc).isoformat()
    }


async def _persist_chat_message(
    db: AsyncSession,
    u_uuid: UUID,
    conversation_id: str,
    question: str,
    answer: str,
    sources: List[Dict[str, Any]],
    model_used: str,
    source_type: str
) -> Dict[str, Any]:
    """Resolve/create the conversation, persist the message, return the response dict."""
    # Resolve the conversation: reuse the one passed in (verify ownership), else
    # create a new one titled from the first question (minimal threading, #21).
    from datetime import datetime, timezone
    conversation = None
    if conversation_id:
        try:
            conversation = await db.get(Conversation, UUID(conversation_id))
        except (ValueError, TypeError):
            conversation = None
        if conversation is None or conversation.user_id != u_uuid:
            conversation = None  # ignore invalid/foreign ids; start a fresh one
    if conversation is None:
        title = question.strip()[:40]
        if len(question.strip()) > 40:
            title += "…"
        conversation = Conversation(user_id=u_uuid, title=title or "New Chat")
        db.add(conversation)
        await db.flush()  # assign conversation.id
    else:
        conversation.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)

    chat_msg = ChatMessage(
        user_id=u_uuid,
        conversation_id=conversation.id,
        question=question,
        answer=answer,
        sources=sources,
        model_used=model_used,
        source_type=source_type
    )
    db.add(chat_msg)
    await db.commit()
    await db.refresh(chat_msg)

    return {
        "id": str(chat_msg.id),
        "conversation_id": str(conversation.id),
        "question": question,
        "answer": answer,
        "sources": sources,
        "model_used": model_used,
        "source_type": source_type,
        "created_at": chat_msg.created_at.isoformat()
    }


async def generate_rag_answer(
    question: str,
    db: AsyncSession,
    user_id: str,
    mode: str = "hybrid",
    conversation_id: str = None
) -> Dict[str, Any]:
    """
    RAG pipeline with hybrid knowledge mode (blocking, non-streaming).

    mode: "hybrid"     — email-grounded answers when relevant context exists; otherwise
                          the LLM answers from its own general knowledge (clearly flagged).
          "email_only" — strict: only answer from synced emails; say "Not mentioned"
                         when nothing relevant is found.
    Returns a dict including 'source_type': email_grounded | general_knowledge | no_emails.
    """
    u_uuid = UUID(user_id)

    answer = ""
    model_used = None
    source_type = "email_grounded"
    used_chunks: List[Dict[str, Any]] = []

    try:
        prep = await _prepare_rag(question, db, u_uuid, mode)
        source_type = prep["source_type"]
        used_chunks = prep["used_chunks"]

        if prep["static_answer"] is not None:
            answer = prep["static_answer"]
            model_used = None
        else:
            answer, model_used = _call_groq(prep["system_prompt"], prep["user_message"], prep["temperature"])

        # Hybrid fallback: if the email-grounded answer admits it couldn't find
        # the information in the synced data, answer from general knowledge instead
        # (clearly flagged). email_only mode keeps the "not mentioned" answer.
        #
        # Confidence gate: only fall back when the top email match was WEAK
        # (< GENERAL_QUESTION_RELEVANCE_THRESHOLD). When emails match strongly, a
        # phrase like "does not mention a specific salary" is just an honest PARTIAL
        # answer to a compound question -> keep the grounded answer instead of
        # discarding the whole thing and losing the parts the emails DID answer.
        if (mode == "hybrid" and source_type == "email_grounded"
                and prep["top_score"] < GENERAL_QUESTION_RELEVANCE_THRESHOLD
                and _answer_is_insufficient(answer)):
            logger.info("Email-grounded answer insufficient AND weak match -> falling back to general knowledge")
            source_type = "general_knowledge"
            answer, model_used = _call_groq(GENERAL_KNOWLEDGE_PROMPT, question, temperature=0.3)
            used_chunks = []

    except Exception as e:
        logger.error(f"RAG pipeline error: {e}", exc_info=True)
        answer = _error_answer(e)
        model_used = None
        source_type = "error"
        used_chunks = []

    sources = _build_sources(source_type, used_chunks)

    # Do not persist transient errors (rate limits, API outages) to chat history.
    if source_type == "error":
        return _error_result(question, answer, conversation_id)

    return await _persist_chat_message(
        db, u_uuid, conversation_id, question, answer, sources, model_used, source_type
    )


async def generate_rag_answer_stream(
    question: str,
    db: AsyncSession,
    user_id: str,
    mode: str = "hybrid",
    conversation_id: str = None
):
    """
    Streaming variant of generate_rag_answer. Yields Server-Sent Events frames:

      {"type": "meta",  "source_type": ...}     — knowledge source decided (pre-answer)
      {"type": "token", "content": "..."}       — an answer text delta
      {"type": "reset", "source_type": ...}     — discard partial answer (hybrid fallback / error)
      {"type": "done",  "message": {...}}       — final persisted ChatMessage payload

    The full answer is persisted to chat history once streaming completes
    (same behavior as the blocking path; errors are not persisted).
    """
    u_uuid = UUID(user_id)

    answer = ""
    model_used = None
    source_type = "email_grounded"
    used_chunks: List[Dict[str, Any]] = []

    try:
        prep = await _prepare_rag(question, db, u_uuid, mode)
        source_type = prep["source_type"]
        used_chunks = prep["used_chunks"]
        yield _sse({"type": "meta", "source_type": source_type})

        if prep["static_answer"] is not None:
            answer = prep["static_answer"]
            yield _sse({"type": "token", "content": answer})
        else:
            model_used = GROQ_MODEL
            async for delta in _stream_groq(prep["system_prompt"], prep["user_message"], prep["temperature"]):
                answer += delta
                yield _sse({"type": "token", "content": delta})

        # Hybrid fallback: the streamed email-grounded answer admitted it couldn't
        # find the info — tell the client to clear it, then stream a clearly-flagged
        # general-knowledge answer instead.
        if (mode == "hybrid" and source_type == "email_grounded"
                and prep["top_score"] < GENERAL_QUESTION_RELEVANCE_THRESHOLD
                and _answer_is_insufficient(answer)):
            logger.info("Email-grounded answer insufficient AND weak match -> falling back to general knowledge (stream)")
            source_type = "general_knowledge"
            used_chunks = []
            answer = ""
            model_used = GROQ_MODEL
            yield _sse({"type": "reset", "source_type": source_type})
            async for delta in _stream_groq(GENERAL_KNOWLEDGE_PROMPT, question, temperature=0.3):
                answer += delta
                yield _sse({"type": "token", "content": delta})

    except Exception as e:
        logger.error(f"RAG streaming error: {e}", exc_info=True)
        answer = _error_answer(e)
        model_used = None
        source_type = "error"
        used_chunks = []
        yield _sse({"type": "reset", "source_type": source_type})
        yield _sse({"type": "token", "content": answer})

    sources = _build_sources(source_type, used_chunks)

    # Do not persist transient errors (rate limits, API outages) to chat history.
    if source_type == "error":
        yield _sse({"type": "done", "message": _error_result(question, answer, conversation_id)})
        return

    result = await _persist_chat_message(
        db, u_uuid, conversation_id, question, answer, sources, model_used, source_type
    )
    yield _sse({"type": "done", "message": result})

