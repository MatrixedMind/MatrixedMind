from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request, Response, status
from fastapi.responses import JSONResponse
from pymongo.errors import PyMongoError
from starlette.middleware.base import RequestResponseEndpoint

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


@app.middleware("http")
async def enforce_llm_body_limit(
    request: Request,
    call_next: RequestResponseEndpoint,
) -> Response:
    if request.url.path.startswith("/api/llm/"):
        content_length = request.headers.get("content-length")
        if content_length is not None:
            try:
                declared_size = int(content_length)
            except ValueError:
                return JSONResponse(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    content={"detail": "Invalid Content-Length"},
                )
            if declared_size > settings.llm_request_body_limit_bytes:
                return JSONResponse(
                    status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                    content={"detail": "Request body too large"},
                )
        body = await request.body()
        if len(body) > settings.llm_request_body_limit_bytes:
            return JSONResponse(
                status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                content={"detail": "Request body too large"},
            )
    return await call_next(request)


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
