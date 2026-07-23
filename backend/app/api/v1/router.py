from fastapi import APIRouter
from .endpoints import auth, oauth, health, gmail, chat, search, audit

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["Auth"])
api_router.include_router(oauth.router, prefix="/oauth", tags=["OAuth"])
api_router.include_router(gmail.router, prefix="/gmail", tags=["Gmail"])
api_router.include_router(chat.router, prefix="/chat", tags=["AI Chat"])
api_router.include_router(search.router, prefix="/search", tags=["Global Search & Analytics"])
api_router.include_router(audit.router, prefix="/audit", tags=["Audit & System Management"])
api_router.include_router(health.router, tags=["Health"])
