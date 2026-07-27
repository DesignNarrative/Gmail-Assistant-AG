from fastapi import APIRouter, Depends, Request, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.schemas.auth import RegisterRequest, LoginRequest, TokenResponse, RefreshRequest, UserResponse, ForgotPasswordRequest
from app.services.auth_service import register_user, authenticate_user, create_user_tokens, refresh_access_token, revoke_token, reset_password
from app.core.database import get_db
from app.core.dependencies import get_current_active_user
from app.core.config import get_settings
from app.models.user import User
import time

router = APIRouter()
settings = get_settings()

# Lightweight in-memory throttle for security-sensitive auth endpoints. Keyed by
# "scope:ip", it caps abusive bursts (brute force / password-reset abuse) on top of
# the global per-IP rate limiter. Single-process local mode needs nothing external.
_AUTH_ATTEMPTS: dict[str, list[float]] = {}

def _throttle(scope: str, ip: str, max_attempts: int = 5, window_seconds: int = 900) -> None:
    now = time.time()
    key = f"{scope}:{ip}"
    recent = [t for t in _AUTH_ATTEMPTS.get(key, []) if now - t < window_seconds]
    if len(recent) >= max_attempts:
        _AUTH_ATTEMPTS[key] = recent
        raise HTTPException(
            status_code=429,
            detail="Too many attempts. Please wait a few minutes and try again."
        )
    recent.append(now)
    _AUTH_ATTEMPTS[key] = recent

@router.post("/register", response_model=UserResponse)
async def register(request: Request, data: RegisterRequest, db: AsyncSession = Depends(get_db)):
    # Access control (Option A): only allow-listed emails may create an account.
    # An empty allowlist means registration is fully closed (fail-safe default).
    allowed = settings.allowed_registration_emails_list
    if data.email.strip().lower() not in allowed:
        raise HTTPException(
            status_code=403,
            detail="Registration is restricted. This email is not authorized to create an account."
        )
    try:
        user = await register_user(db, data)
        return user
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/login", response_model=TokenResponse)
async def login(request: Request, data: LoginRequest, db: AsyncSession = Depends(get_db)):
    ip_address = request.client.host if request.client else ""
    user_agent = request.headers.get("user-agent", "")
    _throttle("login", ip_address, max_attempts=10, window_seconds=900)
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

@router.post("/forgot-password")
async def forgot_password(request: Request, data: ForgotPasswordRequest, db: AsyncSession = Depends(get_db)):
    # Local reset: the app runs on the account owner's own PC, so there is no
    # email delivery step. Only allow-listed emails may reset (same rule as register).
    ip_address = request.client.host if request.client else ""
    _throttle("forgot", ip_address, max_attempts=5, window_seconds=900)
    email = data.email.strip().lower()
    if email not in settings.allowed_registration_emails_list:
        raise HTTPException(
            status_code=403,
            detail="This email is not authorized for this application."
        )
    ok = await reset_password(db, email, data.new_password)
    if not ok:
        raise HTTPException(
            status_code=404,
            detail="No account found with this email. Please sign up first."
        )
    return {"detail": "Password reset successfully. Please sign in with your new password."}

@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_active_user)):
    return current_user
