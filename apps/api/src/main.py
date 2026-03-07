from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI

from src.auth.dependencies import get_current_user
from src.auth.router import router as auth_router
from src.crisis_contacts.router import router as crisis_contacts_router
from src.models.user import User
from src.sessions.router import router as sessions_router
from src.sessions.settings import LiveKitSettings
from src.sources.router import router as sources_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.livekit_settings = LiveKitSettings()
    yield


app = FastAPI(title="Twype API", version="0.1.0", lifespan=lifespan)
app.include_router(auth_router)
app.include_router(crisis_contacts_router, prefix="/crisis-contacts", tags=["crisis-contacts"])
app.include_router(sessions_router, prefix="/sessions", tags=["sessions"])
app.include_router(sources_router, prefix="/sources", tags=["sources"])


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/me")
async def me(user: User = Depends(get_current_user)) -> dict[str, str]:
    return {"user_id": str(user.id), "email": user.email}
