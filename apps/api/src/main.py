from fastapi import Depends, FastAPI

from src.auth.dependencies import get_current_user
from src.auth.router import router as auth_router
from src.models.user import User

app = FastAPI(title="Twype API", version="0.1.0")
app.include_router(auth_router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/me")
async def me(user: User = Depends(get_current_user)) -> dict[str, str]:
    return {"user_id": str(user.id), "email": user.email}
