from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, desc
from app.core.database import get_db
from app.core.dependencies import get_current_active_user
from app.models.user import User
from app.models.chat_message import ChatMessage
from app.models.conversation import Conversation
from app.services.ai.rag_service import generate_rag_answer, generate_rag_answer_stream
from typing import List, Optional, Any
import logging
import io

router = APIRouter()
logger = logging.getLogger(__name__)

class AskQuestionRequest(BaseModel):
    question: str = Field(..., min_length=2, max_length=1000, description="The natural language question to ask the AI")
    mode: str = Field(default="hybrid", description="hybrid = email-grounded + general-knowledge fallback; email_only = strict")
    conversation_id: Optional[str] = Field(default=None, description="Existing conversation to append to; a new one is created when omitted")

class SourceCitation(BaseModel):
    filename: str
    chunk_text: str
    score: float

class ChatMessageResponse(BaseModel):
    id: str
    conversation_id: Optional[str] = None
    question: str
    answer: Optional[str]
    sources: List[Any]
    model_used: Optional[str]
    source_type: Optional[str] = None
    created_at: str

class ConversationResponse(BaseModel):
    id: str
    title: Optional[str]
    created_at: str
    updated_at: Optional[str]

@router.post("/ask", response_model=ChatMessageResponse)
async def ask_question(
    req: AskQuestionRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    try:
        logger.info(f"User {current_user.email} asked: '{req.question}'")
        mode = req.mode if req.mode in ("hybrid", "email_only") else "hybrid"
        result = await generate_rag_answer(
            question=req.question.strip(),
            db=db,
            user_id=str(current_user.id),
            mode=mode,
            conversation_id=req.conversation_id
        )
        return result
    except Exception as e:
        logger.error(f"Chat RAG generation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate answer: {str(e)}")


@router.post("/ask/stream")
async def ask_question_stream(
    req: AskQuestionRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Streaming variant of /ask. Returns Server-Sent Events frames:
    meta -> token* -> (reset -> token*)? -> done (with the persisted message).
    """
    logger.info(f"User {current_user.email} asked (stream): '{req.question}'")
    mode = req.mode if req.mode in ("hybrid", "email_only") else "hybrid"
    return StreamingResponse(
        generate_rag_answer_stream(
            question=req.question.strip(),
            db=db,
            user_id=str(current_user.id),
            mode=mode,
            conversation_id=req.conversation_id
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # disable proxy buffering (nginx)
        }
    )

@router.get("/conversations", response_model=List[ConversationResponse])
async def list_conversations(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """List the user's conversations, most recently updated first."""
    try:
        stmt = (
            select(Conversation)
            .where(Conversation.user_id == current_user.id)
            .order_by(desc(Conversation.updated_at), desc(Conversation.created_at))
        )
        result = await db.execute(stmt)
        convs = result.scalars().all()
        return [
            {
                "id": str(c.id),
                "title": c.title,
                "created_at": c.created_at.isoformat() if c.created_at else "",
                "updated_at": c.updated_at.isoformat() if c.updated_at else None,
            }
            for c in convs
        ]
    except Exception as e:
        logger.error(f"Error listing conversations: {e}")
        raise HTTPException(status_code=500, detail="Failed to list conversations")


async def _get_owned_conversation(conversation_id: str, user: User, db: AsyncSession) -> Conversation:
    from uuid import UUID as _UUID
    try:
        cid = _UUID(conversation_id)
    except (ValueError, TypeError):
        raise HTTPException(status_code=404, detail="Conversation not found")
    conv = await db.get(Conversation, cid)
    if conv is None or conv.user_id != user.id:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conv


@router.get("/conversations/{conversation_id}", response_model=List[ChatMessageResponse])
async def get_conversation_messages(
    conversation_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Return all messages in a conversation, in chronological order."""
    await _get_owned_conversation(conversation_id, current_user, db)
    stmt = (
        select(ChatMessage)
        .where(ChatMessage.conversation_id == conversation_id)
        .order_by(ChatMessage.created_at)
    )
    result = await db.execute(stmt)
    messages = result.scalars().all()
    return [
        {
            "id": str(msg.id),
            "conversation_id": str(msg.conversation_id) if msg.conversation_id else None,
            "question": msg.question,
            "answer": msg.answer,
            "sources": msg.sources or [],
            "model_used": msg.model_used,
            "source_type": msg.source_type,
            "created_at": msg.created_at.isoformat(),
        }
        for msg in messages
    ]


@router.delete("/conversations/{conversation_id}")
async def delete_conversation(
    conversation_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete a conversation and its messages (cascade)."""
    conv = await _get_owned_conversation(conversation_id, current_user, db)
    await db.delete(conv)
    await db.commit()
    return {"detail": "Conversation deleted"}


@router.get("/history", response_model=List[ChatMessageResponse])
async def get_chat_history(
    limit: int = 50,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    try:
        stmt = (
            select(ChatMessage)
            .where(ChatMessage.user_id == current_user.id)
            .order_by(desc(ChatMessage.created_at))
            .limit(limit)
        )
        result = await db.execute(stmt)
        messages = result.scalars().all()
        
        output = []
        for msg in reversed(messages):  # chronological order for UI
            output.append({
                "id": str(msg.id),
                "question": msg.question,
                "answer": msg.answer,
                "sources": msg.sources or [],
                "model_used": msg.model_used,
                "source_type": msg.source_type,
                "created_at": msg.created_at.isoformat()
            })
        return output
    except Exception as e:
        logger.error(f"Error fetching chat history: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch chat history")

@router.delete("/history")
async def clear_chat_history(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    try:
        stmt = delete(ChatMessage).where(ChatMessage.user_id == current_user.id)
        await db.execute(stmt)
        await db.commit()
        return {"detail": "Chat history cleared successfully"}
    except Exception as e:
        logger.error(f"Error clearing chat history: {e}")
        raise HTTPException(status_code=500, detail="Failed to clear chat history")


@router.get("/export")
async def export_chat_history(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    try:
        from datetime import datetime
        stmt = (
            select(ChatMessage)
            .where(ChatMessage.user_id == current_user.id)
            .order_by(desc(ChatMessage.created_at))
        )
        result = await db.execute(stmt)
        messages = result.scalars().all()

        output = io.StringIO()
        output.write("==================================================\n")
        output.write("   Abhinav Group AI Gmail Assistant Chat Export\n")
        output.write(f"   Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        output.write(f"   User: {current_user.email}\n")
        output.write("==================================================\n\n")

        for msg in reversed(messages):  # chronological order
            output.write(f"👤 Question: {msg.question}\n\n")
            output.write(f"🤖 Answer:\n{msg.answer}\n\n")
            if msg.sources:
                output.write("Sources Cited:\n")
                for s in msg.sources:
                    output.write(f" - {s.get('filename')} (relevance: {s.get('score')})\n")
            output.write("\n" + "-"*50 + "\n\n")

        output.seek(0)
        return StreamingResponse(
            io.BytesIO(output.getvalue().encode("utf-8")),
            media_type="text/plain",
            headers={"Content-Disposition": "attachment; filename=chat_history.txt"}
        )
    except Exception as e:
        logger.error(f"Error exporting chat history: {e}")
        raise HTTPException(status_code=500, detail="Failed to export chat history")

