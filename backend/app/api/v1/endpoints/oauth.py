from fastapi import APIRouter, HTTPException, Depends, Query, Request
from fastapi.responses import RedirectResponse
from urllib.parse import urlparse
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


def _resolve_frontend_origin(request: Request) -> str:
    """
    Best-effort detection of the frontend origin that initiated the OAuth flow.
    Priority: Origin header -> Referer (scheme://host) -> first allowed origin
              -> request base URL. Works for single-process (frontend served by
              the backend on the same port) and split (frontend on its own port)
              deployments. NOTE: only meaningful on the /oauth/google request
              (which genuinely comes from the frontend). The /callback request
              comes from Google, so it must rely on the origin carried in the
              state token instead.
    """
    origin = request.headers.get("origin")
    if origin:
        return origin.rstrip("/")
    referer = request.headers.get("referer")
    if referer:
        try:
            parsed = urlparse(referer)
            if parsed.scheme and parsed.netloc:
                return f"{parsed.scheme}://{parsed.netloc}"
        except Exception:
            pass
    if settings.allowed_origins_list:
        return settings.allowed_origins_list[0].rstrip("/")
    return str(request.base_url).rstrip("/")


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
async def google_auth(request: Request, current_user: User = Depends(get_current_active_user)):
    if not settings.GOOGLE_CLIENT_ID or not settings.GOOGLE_CLIENT_SECRET:
        raise HTTPException(status_code=500, detail="Google OAuth credentials are not configured in settings")
    
    try:
        flow = get_google_flow()
        # Capture the frontend origin so the callback knows where to redirect
        # the browser back to (carried inside the OAuth state token).
        frontend_origin = _resolve_frontend_origin(request)
        state = create_state_token(str(current_user.id), frontend_origin)
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
    request: Request,
    code: str = Query(None),
    state: str = Query(None),
    error: str = Query(None),
    db: AsyncSession = Depends(get_db)
):
    # Resolve the frontend origin to redirect the browser back to. It is carried
    # inside the OAuth state token (Google round-trips `state` unchanged), which
    # is reliable because the /callback request itself comes from Google (so its
    # own Origin/Referer headers point at Google, not the frontend). Fall back to
    # the first configured allowed origin when the state is missing/malformed.
    decoded_state = decode_state_token(state) if state else None
    frontend_origin = (decoded_state or {}).get("frontend_origin") or ""
    if not frontend_origin and settings.allowed_origins_list:
        frontend_origin = settings.allowed_origins_list[0].rstrip("/")
    redirect_base = frontend_origin.rstrip("/")

    if error:
        logger.error(f"OAuth callback error: {error}")
        return RedirectResponse(url=f"{redirect_base}/dashboard?error={error}")

    if not code or not state:
        raise HTTPException(status_code=400, detail="Missing required OAuth parameters")

    user_id = (decoded_state or {}).get("user_id")
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
        return RedirectResponse(url=f"{redirect_base}/dashboard?sync_connected=true")
    except Exception as e:
        logger.error(f"Error in OAuth callback processing: {e}")
        await db.rollback()
        return RedirectResponse(url=f"{redirect_base}/dashboard?error=oauth_processing_failed")
