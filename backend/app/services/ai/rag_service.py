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
                "'Director's AI Assistant' label. Once synced, I can answer any question based on those emails and attachments."
            )
            model_used = None
        else:
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

            client = Groq(api_key=settings.GROQ_API_KEY)
            response = client.chat.completions.create(
                model=GROQ_MODEL,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_message}
                ],
                temperature=0.1,
                max_tokens=3000
            )
            answer = response.choices[0].message.content.strip()
            model_used = GROQ_MODEL

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
