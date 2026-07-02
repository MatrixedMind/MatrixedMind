from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, status
from pymongo.errors import PyMongoError

from app.adapters.mongo.connection import MongoConnection
from app.api.routes import router as api_router
from app.settings import settings
from app.web.routes import router as web_router


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None, None]:
    MongoConnection.connect()
    yield
    MongoConnection.disconnect()


app = FastAPI(title="MatrixedMind", lifespan=lifespan)

app.include_router(api_router, prefix="/api")
app.include_router(web_router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "env": settings.app_env}


@app.get("/ready")
async def ready() -> dict[str, str]:
    try:
        MongoConnection.ping()
    except PyMongoError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="MongoDB is not ready",
        ) from exc

    return {"status": "ok", "mongo": "ok"}
