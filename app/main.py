from fastapi import FastAPI

from app.api.routes import router as api_router
from app.settings import settings
from app.web.routes import router as web_router

app = FastAPI(title="Wiki App")

app.include_router(api_router, prefix="/api")
app.include_router(web_router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "env": settings.app_env}
