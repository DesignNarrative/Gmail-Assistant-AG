from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.database import check_db_connection
from app.middleware.audit_middleware import AuditMiddleware
from app.middleware.rate_limit_middleware import RateLimitMiddleware
from app.core.logging_config import setup_logging
import logging
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
import os
import asyncio

settings = get_settings()
setup_logging()
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting up InboxIQ")
    db_ok = await check_db_connection()
    if db_ok:
        logger.info("Database connection successful.")
        if settings.FIRST_DIRECTOR_EMAIL:
            from app.core.database import AsyncSessionLocal
            from app.services.auth_service import get_user_by_email
            from app.models.user import User
            from app.core.security import hash_password
            async with AsyncSessionLocal() as db:
                existing = await get_user_by_email(db, settings.FIRST_DIRECTOR_EMAIL)
                if not existing:
                    logger.info(f"Bootstrapping first director: {settings.FIRST_DIRECTOR_EMAIL}")
                    director = User(
                        email=settings.FIRST_DIRECTOR_EMAIL,
                        full_name=settings.FIRST_DIRECTOR_NAME or "Director",
                        hashed_password=hash_password(settings.FIRST_DIRECTOR_PASSWORD),
                        role="director",
                        is_active=True,
                        is_email_verified=True
                    )
                    db.add(director)
                    await db.commit()
                    logger.info("Bootstrapping complete.")
        
        # Start the daily sync scheduler
        from app.workers.sync_tasks import run_daily_sync_scheduler_task
        app.state.sync_scheduler_task = asyncio.create_task(run_daily_sync_scheduler_task())
        logger.info("Daily sync scheduler task initialized.")
    else:
        logger.error("Database connection failed.")
    yield
    
    # Cancel daily sync scheduler on shutdown
    if hasattr(app.state, "sync_scheduler_task"):
        logger.info("Stopping daily sync scheduler task...")
        app.state.sync_scheduler_task.cancel()
        try:
            await app.state.sync_scheduler_task
        except asyncio.CancelledError:
            pass
    logger.info("Shutting down InboxIQ")

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(AuditMiddleware)
app.add_middleware(RateLimitMiddleware)

app.include_router(api_router, prefix="/api/v1")

@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request, exc):
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    return JSONResponse(status_code=422, content={"detail": exc.errors()})

@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})

# Serve static assets compiled from the frontend build
assets_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../frontend/dist/assets"))
if os.path.isdir(assets_dir):
    app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

@app.get("/health")
async def health_check():
    db_ok = await check_db_connection()
    return {"status": "ok", "db_connected": db_ok, "version": settings.APP_VERSION}

# Catch-all route to serve the React SPA index.html for client-side routing
@app.get("/{fallback_path:path}", include_in_schema=False)
async def spa_fallback(request: Request, fallback_path: str):
    # API endpoints and docs must return 404 if they do not match any defined route
    if fallback_path.startswith("api/") or fallback_path.startswith("docs") or fallback_path == "openapi.json":
        return JSONResponse(status_code=404, content={"detail": "Not Found"})
    
    base_dist_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../frontend/dist"))
    public_file_path = os.path.abspath(os.path.join(base_dist_dir, fallback_path))
    
    # Path traversal protection: ensure resolved path is strictly within frontend/dist
    if not public_file_path.startswith(base_dist_dir):
        return JSONResponse(status_code=403, content={"detail": "Access forbidden"})
    
    if os.path.isfile(public_file_path):
        return FileResponse(public_file_path)
        
    index_path = os.path.join(base_dist_dir, "index.html")
    if os.path.isfile(index_path):
        return FileResponse(index_path)
    return JSONResponse(status_code=404, content={"detail": "Frontend not found"})
