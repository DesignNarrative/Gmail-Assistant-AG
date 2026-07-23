from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models.user import User
from app.models.refresh_token import RefreshToken
from app.schemas.auth import RegisterRequest
from app.core.security import hash_password, verify_password, create_access_token, create_refresh_token, generate_token_hash, decode_token
from app.core.config import get_settings
import uuid
from datetime import datetime, timezone, timedelta

settings = get_settings()

from sqlalchemy import func

async def get_user_by_email(db: AsyncSession, email: str) -> User | None:
    clean_email = email.strip().lower() if email else ""
    result = await db.execute(select(User).where(func.lower(User.email) == clean_email))
    return result.scalars().first()

async def register_user(db: AsyncSession, data: RegisterRequest) -> User:
    existing = await get_user_by_email(db, data.email)
    if existing:
        raise ValueError("Email already registered")
    user = User(
        email=data.email,
        full_name=data.full_name,
        hashed_password=hash_password(data.password)
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user

async def authenticate_user(db: AsyncSession, email: str, password: str) -> User | None:
    user = await get_user_by_email(db, email)
    if not user:
        return None
    now_naive = datetime.now(timezone.utc).replace(tzinfo=None)
    if user.locked_until and user.locked_until > now_naive:
        return None
    if not user.hashed_password or not verify_password(password, user.hashed_password):
        user.failed_login_attempts += 1
        if user.failed_login_attempts >= 5:
            user.locked_until = now_naive + timedelta(minutes=15)
        await db.commit()
        return None
    user.failed_login_attempts = 0
    user.locked_until = None
    user.last_login_at = now_naive
    await db.commit()
    return user

async def create_user_tokens(db: AsyncSession, user: User, ip: str, user_agent: str) -> dict:
    access_token = create_access_token({"sub": str(user.id)})
    refresh_token = create_refresh_token({"sub": str(user.id)})
    now_naive = datetime.now(timezone.utc).replace(tzinfo=None)
    rt = RefreshToken(
        user_id=user.id,
        token_hash=generate_token_hash(refresh_token),
        expires_at=now_naive + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
        ip_address=ip,
        user_agent=user_agent
    )
    db.add(rt)
    await db.commit()
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    }

async def refresh_access_token(db: AsyncSession, token: str) -> dict:
    payload = decode_token(token)
    if not payload or payload.get("type") != "refresh":
        raise ValueError("Invalid token")
    token_hash = generate_token_hash(token)
    result = await db.execute(select(RefreshToken).where(RefreshToken.token_hash == token_hash, RefreshToken.revoked == False))
    rt = result.scalars().first()
    now_naive = datetime.now(timezone.utc).replace(tzinfo=None)
    if not rt or rt.expires_at < now_naive:
        raise ValueError("Token expired or revoked")
    
    access_token = create_access_token({"sub": str(rt.user_id)})
    return {
        "access_token": access_token,
        "refresh_token": token,
        "token_type": "bearer",
        "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    }

async def revoke_token(db: AsyncSession, token: str) -> bool:
    token_hash = generate_token_hash(token)
    result = await db.execute(select(RefreshToken).where(RefreshToken.token_hash == token_hash))
    rt = result.scalars().first()
    if rt:
        rt.revoked = True
        rt.revoked_at = datetime.now(timezone.utc).replace(tzinfo=None)
        await db.commit()
        return True
    return False
