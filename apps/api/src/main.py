import logging
import os
from contextlib import asynccontextmanager

import resend
from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text as sa_text
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.dependencies import get_current_user, get_session
from src.auth.router import router as auth_router
from src.crisis_contacts.router import router as crisis_contacts_router
from src.models.user import User
from src.sessions.router import router as sessions_router
from src.sessions.settings import LiveKitSettings
from src.sources.router import router as sources_router

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.livekit_settings = LiveKitSettings()
    resend.api_key = os.environ.get("RESEND_API_KEY", "")
    yield


app = FastAPI(title="Twype API", version="0.1.0", lifespan=lifespan)

_cors_origins = os.environ.get("CORS_ALLOWED_ORIGINS", "http://localhost:5173")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in _cors_origins.split(",") if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(crisis_contacts_router, prefix="/crisis-contacts", tags=["crisis-contacts"])
app.include_router(sessions_router, prefix="/sessions", tags=["sessions"])
app.include_router(sources_router, prefix="/sources", tags=["sources"])


@app.get("/health")
async def health(db: AsyncSession = Depends(get_session)):
    try:
        await db.execute(sa_text("SELECT 1"))
    except Exception:
        logger.warning("Health check DB query failed", exc_info=True)
        return JSONResponse(
            status_code=503,
            content={"status": "degraded", "db": "unreachable"},
        )
    return {"status": "ok"}


@app.get("/me")
async def me(user: User = Depends(get_current_user)) -> dict[str, str]:
    return {"user_id": str(user.id), "email": user.email}
