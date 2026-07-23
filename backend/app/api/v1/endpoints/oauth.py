from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from google_auth_oauthlib.flow import Flow
from app.core.config import get_settings
from app.core.database import get_db
from app.core.dependencies import get_current_active_user
from app.core.security import create_state_token, decode_state_token, encrypt_value
from app.models.user import User
from app.services.auth_service import get_user_by_email
from sqlalchemy import update
import logging

router = APIRouter()
settings = get_settings()
logger = logging.getLogger(__name__)

def get_google_flow() -> Flow:
    client_config = {
        "web": {
            "client_id": settings.GOOGLE_CLIENT_ID,
            "client_secret": settings.GOOGLE_CLIENT_SECRET,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [settings.GOOGLE_REDIRECT_URI]
        }
    }
    flow = Flow.from_client_config(
        client_config,
        scopes=["https://www.googleapis.com/auth/gmail.readonly"]
    )
    flow.redirect_uri = settings.GOOGLE_REDIRECT_URI
    return flow

@router.get("/google")
async def google_auth(current_user: User = Depends(get_current_active_user)):
    if not settings.GOOGLE_CLIENT_ID or not settings.GOOGLE_CLIENT_SECRET:
        raise HTTPException(status_code=500, detail="Google OAuth credentials are not configured in settings")
    
    try:
        flow = get_google_flow()
        state = create_state_token(str(current_user.id))
        authorization_url, _ = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            prompt='consent',
            state=state
        )
        return {"url": authorization_url}
    except Exception as e:
        logger.error(f"Error generating OAuth URL: {e}")
        raise HTTPException(status_code=500, detail="Failed to initialize OAuth flow")

@router.get("/callback")
async def google_callback(
    code: str = Query(None),
    state: str = Query(None),
    error: str = Query(None),
    db: AsyncSession = Depends(get_db)
):
    if error:
        logger.error(f"OAuth callback error: {error}")
        return RedirectResponse(url=f"{settings.ALLOWED_ORIGINS}?error={error}")
        
    if not code or not state:
        raise HTTPException(status_code=400, detail="Missing required OAuth parameters")
        
    user_id = decode_state_token(state)
    if not user_id:
        raise HTTPException(status_code=400, detail="Invalid or expired state parameter")
        
    try:
        flow = get_google_flow()
        flow.fetch_token(code=code)
        credentials = flow.credentials
        
        # Encrypt tokens for storage at rest
        enc_access_token = encrypt_value(credentials.token)
        enc_refresh_token = encrypt_value(credentials.refresh_token) if credentials.refresh_token else None
        
        # Find user and update Google auth attributes
        stmt = update(User).where(User.id == user_id).values(
            google_access_token=enc_access_token,
            is_email_verified=True
        )
        
        # Only overwrite refresh token if Google returned one (consent prompted)
        if enc_refresh_token:
            stmt = stmt.values(google_refresh_token=enc_refresh_token)
            
        await db.execute(stmt)
        await db.commit()
        
        logger.info(f"Successfully connected Gmail for user {user_id}")
        return RedirectResponse(url=f"http://localhost:3000/dashboard?sync_connected=true")
    except Exception as e:
        logger.error(f"Error in OAuth callback processing: {e}")
        await db.rollback()
        return RedirectResponse(url=f"http://localhost:3000/dashboard?error=oauth_processing_failed")
