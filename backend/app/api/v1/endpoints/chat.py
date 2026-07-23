from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, desc
from app.core.database import get_db
from app.core.dependencies import get_current_active_user
from app.models.user import User
from app.models.chat_message import ChatMessage
from app.services.ai.rag_service import generate_rag_answer
from typing import List, Optional, Any
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

class AskQuestionRequest(BaseModel):
    question: str = Field(..., min_length=2, max_length=1000, description="The natural language question to ask the AI")

class SourceCitation(BaseModel):
    filename: str
    chunk_text: str
    score: float

class ChatMessageResponse(BaseModel):
    id: str
    question: str
    answer: Optional[str]
    sources: List[Any]
    model_used: Optional[str]
    created_at: str

@router.post("/ask", response_model=ChatMessageResponse)
async def ask_question(
    req: AskQuestionRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    try:
        logger.info(f"User {current_user.email} asked: '{req.question}'")
        result = await generate_rag_answer(
            question=req.question.strip(),
            db=db,
            user_id=str(current_user.id)
        )
        return result
    except Exception as e:
        logger.error(f"Chat RAG generation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate answer: {str(e)}")

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
