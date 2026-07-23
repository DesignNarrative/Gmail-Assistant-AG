from fastapi import APIRouter, Depends, Request, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.schemas.auth import RegisterRequest, LoginRequest, TokenResponse, RefreshRequest, UserResponse
from app.services.auth_service import register_user, authenticate_user, create_user_tokens, refresh_access_token, revoke_token
from app.core.database import get_db
from app.core.dependencies import get_current_active_user
from app.models.user import User

router = APIRouter()

@router.post("/register", response_model=UserResponse)
async def register(request: Request, data: RegisterRequest, db: AsyncSession = Depends(get_db)):
    try:
        user = await register_user(db, data)
        return user
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/login", response_model=TokenResponse)
async def login(request: Request, data: LoginRequest, db: AsyncSession = Depends(get_db)):
    ip_address = request.client.host if request.client else ""
    user_agent = request.headers.get("user-agent", "")
    user = await authenticate_user(db, data.email, data.password)
    if not user:
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    tokens = await create_user_tokens(db, user, ip_address, user_agent)
    return tokens

@router.post("/refresh", response_model=TokenResponse)
async def refresh(data: RefreshRequest, db: AsyncSession = Depends(get_db)):
    try:
        tokens = await refresh_access_token(db, data.refresh_token)
        return tokens
    except Exception as e:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

@router.post("/logout")
async def logout(data: RefreshRequest, db: AsyncSession = Depends(get_db)):
    await revoke_token(db, data.refresh_token)
    return {"detail": "Logged out successfully"}

@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_active_user)):
    return current_user
