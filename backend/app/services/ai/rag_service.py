from typing import List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text, select, desc
from app.models.chat_message import ChatMessage
from app.models.document_chunk import DocumentChunk
from app.models.attachment import Attachment
from app.models.email import Email
from app.services.ai.embedding_service import generate_single_embedding
from app.core.config import get_settings
import logging
import httpx
from uuid import UUID

logger = logging.getLogger(__name__)
settings = get_settings()

GROQ_MODEL = settings.GROQ_MODEL
MAX_CONTEXT_CHUNKS = 15
MAX_CONTEXT_CHARS = 14000

SYSTEM_PROMPT = """You are InboxIQ — an AI email assistant. You have access to the user's synced Gmail emails, PDFs, attachments, and documents.

RULES (follow strictly, no exceptions):

1. ANSWER ONLY WHAT IS ASKED. Nothing more. No unsolicited advice, no risk flags, no "expert takeaways", no "strategic recommendations" unless the user explicitly asks for them.

2. BE CONCISE. Give the direct answer first. Use tables or bullets only when they genuinely help present the data. Do not pad answers.

3. CITATIONS. Cite the source email or file once, at the end of the answer:
   > 📧 "Subject" — From: Name — Date: DD Mon YYYY
   > 📎 filename.pdf

4. ACCURACY. Only use facts from the provided email context. If something is not in the context, say "Not found in your emails."

5. NO UNNECESSARY SECTIONS. Do not add "Expert Analysis", "Risk Flags", "Recommendations", "Strategic Advice", or "Bottom-Line Summary" unless specifically asked.

6. FORMAT. Use markdown. Keep it clean and readable.
"""


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
            "similarity_score": float(row.similarity_score)
        })

    logger.info(f"Retrieved {len(chunks)} relevant chunks for user {user_id}: '{question[:80]}'")
    return chunks


async def fetch_full_email_catalog(db: AsyncSession, user_id: UUID, max_chars: int = 10000) -> str:
    """
    Build a comprehensive catalog of synced emails for the user, safely bounded to prevent LLM token overflow.
    """
    stmt = select(Email).where(Email.user_id == user_id).order_by(desc(Email.date_sent)).limit(50)
    emails = (await db.execute(stmt)).scalars().all()

    if not emails:
        return "No emails found in the database."

    lines = ["═══ EMAIL CATALOG (InboxIQ Synced Label) ═══\n"]
    current_chars = 0

    for i, e in enumerate(emails, 1):
        att_stmt = select(Attachment).where(Attachment.email_id == e.id)
        atts = (await db.execute(att_stmt)).scalars().all()
        att_names = ", ".join([f"{a.filename} ({a.mime_type})" for a in atts]) if atts else "None"

        body = e.body_text or e.snippet or "(No body content)"
        # Include full preview for first 15 emails; compact preview for subsequent emails
        max_preview = 800 if i <= 15 else 200
        body_preview = body[:max_preview] + ("..." if len(body) > max_preview else "")

        entry = (
            f"── EMAIL #{i} ──\n"
            f"Subject: {e.subject}\n"
            f"From: {e.sender_name or ''} <{e.sender_email}>\n"
            f"Date: {e.date_sent or e.date_received}\n"
            f"Attachments: {att_names}\n"
            f"Body:\n{body_preview}\n\n"
        )
        if current_chars + len(entry) > max_chars:
            lines.append(f"... [plus {len(emails) - i + 1} more emails in inbox]")
            break
        lines.append(entry)
        current_chars += len(entry)

    return "\n".join(lines)


async def _call_gemini_fallback(system_prompt: str, user_message: str) -> tuple[str, str]:
    """
    Fallback call to Google Gemini with model candidate rotation.
    Runs asynchronously via httpx with no thread blocking.
    Returns: (answer_text, model_name_used)
    """
    if not settings.GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY is not configured in settings.")

    candidate_models = [settings.GEMINI_MODEL, "gemini-3.5-flash", "gemini-3.5-flash-lite", "gemini-3.7-flash"]
    candidate_models = list(dict.fromkeys([m for m in candidate_models if m]))

    last_err = None
    async with httpx.AsyncClient(timeout=25.0) as http_client:
        for model_name in candidate_models:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={settings.GEMINI_API_KEY}"
            payload = {
                "systemInstruction": {
                    "parts": [{"text": system_prompt}]
                },
                "contents": [
                    {
                        "role": "user",
                        "parts": [{"text": user_message}]
                    }
                ],
                "generationConfig": {
                    "temperature": 0.1,
                    "maxOutputTokens": 3000
                }
            }
            try:
                resp = await http_client.post(url, json=payload)
                if resp.status_code == 200:
                    data = resp.json()
                    candidates = data.get("candidates", [])
                    if candidates:
                        parts = candidates[0].get("content", {}).get("parts", [])
                        if parts and "text" in parts[0]:
                            return parts[0]["text"].strip(), model_name
                logger.warning(f"Gemini candidate {model_name} returned HTTP {resp.status_code}: {resp.text[:120]}")
                last_err = RuntimeError(f"Gemini {model_name} returned {resp.status_code}")
            except Exception as candidate_err:
                logger.warning(f"Gemini candidate {model_name} failed: {candidate_err}")
                last_err = candidate_err

    raise last_err or RuntimeError("All Gemini candidate models failed.")


async def _call_openai_fallback(system_prompt: str, user_message: str) -> tuple[str, str]:
    """
    Fallback call to OpenAI (gpt-4o-mini).
    Runs asynchronously via httpx with no thread blocking.
    Returns: (answer_text, model_name_used)
    """
    if not settings.OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY is not configured in settings.")

    model_name = settings.OPENAI_MODEL or "gpt-4o-mini"
    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": model_name,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ],
        "temperature": 0.1,
        "max_tokens": 3000
    }

    async with httpx.AsyncClient(timeout=25.0) as http_client:
        resp = await http_client.post(url, headers=headers, json=payload)
        if resp.status_code != 200:
            raise RuntimeError(f"OpenAI API returned {resp.status_code}: {resp.text[:120]}")
        data = resp.json()
        return data["choices"][0]["message"]["content"].strip(), model_name


async def generate_rag_answer(
    question: str,
    db: AsyncSession,
    user_id: str
) -> Dict[str, Any]:
    """
    Full RAG pipeline: vector similarity search + full email catalog injection + Groq LLaMA 3.3 70B.
    """
    from groq import Groq
    u_uuid = UUID(user_id)

    # Check how many vector chunks exist for this specific user
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

    context_parts = []
    used_chunks = []
    answer = ""
    model_used = None

    try:
        # Always inject full email catalog for broad queries OR when chunks are low
        if is_broad_query or chunk_count < 5:
            email_catalog = await fetch_full_email_catalog(db, u_uuid)
            context_parts.append(email_catalog)

        # Add vector-retrieved chunks (most relevant content)
        if chunk_count > 0:
            chunks = await retrieve_relevant_chunks(question, db, u_uuid)
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
            # No data at all — tell the user to sync
            answer = (
                "⚠️ **No emails or documents have been synced yet.**\n\n"
                "Please go to the **Dashboard** and click **'Sync Labeled Emails'** to import your Gmail data from the "
                "'InboxIQ' label. Once synced, I can answer any question based on those emails and attachments."
            )
            model_used = None
        else:
            context_text = "\n\n---\n\n".join(context_parts)

            user_message = f"""CONTEXT — User's synced Gmail emails and documents:

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

            # ── Tier 1: Primary Fast Engine (Groq) ──────────────────────────
            if settings.GROQ_API_KEY:
                client = Groq(api_key=settings.GROQ_API_KEY)
                candidate_models = [settings.GROQ_MODEL, "openai/gpt-oss-120b", "openai/gpt-oss-20b", "qwen/qwen3.8-27b"]
                models_to_try = list(dict.fromkeys([m for m in candidate_models if m]))
                
                response = None
                last_err = None
                for model_candidate in models_to_try:
                    try:
                        response = client.chat.completions.create(
                            model=model_candidate,
                            messages=[
                                {"role": "system", "content": SYSTEM_PROMPT},
                                {"role": "user", "content": user_message}
                            ],
                            temperature=0.1,
                            max_tokens=3000
                        )
                        model_used = model_candidate
                        answer = response.choices[0].message.content.strip()
                        break
                    except Exception as model_err:
                        logger.warning(f"Groq model {model_candidate} failed: {model_err}. Trying next candidate...")
                        last_err = model_err

            # ── Tier 2: Secondary Fallback (Google Gemini) ───────────────────
            if not answer and settings.GEMINI_API_KEY:
                logger.warning(f"Groq unavailable or failed. Failing over to Google Gemini...")
                try:
                    answer, gemini_model = await _call_gemini_fallback(SYSTEM_PROMPT, user_message)
                    model_used = f"{gemini_model} (fallback)"
                    logger.info(f"Gemini fallback succeeded using {model_used}!")
                except Exception as gemini_err:
                    logger.error(f"Gemini fallback also failed: {gemini_err}. Trying OpenAI...")
                    last_err = gemini_err

            # ── Tier 3: Tertiary Fallback (OpenAI) ────────────────────────────
            if not answer and settings.OPENAI_API_KEY:
                logger.warning(f"Failing over to OpenAI...")
                try:
                    answer, openai_model = await _call_openai_fallback(SYSTEM_PROMPT, user_message)
                    model_used = f"{openai_model} (fallback)"
                    logger.info(f"OpenAI fallback succeeded using {model_used}!")
                except Exception as openai_err:
                    logger.error(f"OpenAI fallback also failed: {openai_err}")
                    last_err = openai_err

            if not answer:
                raise last_err or Exception("All AI providers (Groq, Gemini, OpenAI) failed to generate a response.")

    except Exception as e:
        logger.error(f"RAG pipeline error: {e}", exc_info=True)
        answer = f"⚠️ **AI Service Error**: {str(e)}\n\nPlease check your Groq API key or try again shortly."
        model_used = None

    # Save chat message to history
    sources = [
        {
            "filename": c["filename"],
            "chunk_text": c["chunk_text"][:300],
            "score": round(c["similarity_score"], 3)
        }
        for c in used_chunks
    ]

    chat_msg = ChatMessage(
        user_id=u_uuid,
        question=question,
        answer=answer,
        sources=sources,
        model_used=model_used
    )
    db.add(chat_msg)
    await db.commit()
    await db.refresh(chat_msg)

    return {
        "id": str(chat_msg.id),
        "question": question,
        "answer": answer,
        "sources": sources,
        "model_used": model_used,
        "created_at": chat_msg.created_at.isoformat()
    }
