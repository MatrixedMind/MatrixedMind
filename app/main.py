from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request, Response, status
from fastapi.responses import JSONResponse
from pymongo.errors import PyMongoError
from starlette.middleware.base import RequestResponseEndpoint
from starlette.staticfiles import StaticFiles

from app.adapters.mongo.connection import MongoConnection
from app.api.routes import router as api_router
from app.auth.dependencies import clear_session_cookies, set_session_cookies
from app.openapi import build_llm_openapi_schema
from app.settings import settings
from app.web.routes import router as web_router


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None, None]:
    MongoConnection.connect()
    yield
    MongoConnection.disconnect()


app = FastAPI(title="MatrixedMind", lifespan=lifespan)
app.mount("/static", StaticFiles(directory="app/web/static"), name="static")


@app.middleware("http")
async def refresh_browser_session_cookie(
    request: Request,
    call_next: RequestResponseEndpoint,
) -> Response:
    request.state.browser_session = None
    request.state.csrf_token = ""
    response = await call_next(request)
    if getattr(request.state, "suppress_session_refresh", False):
        clear_session_cookies(response)
    else:
        values = getattr(request.state, "session_cookie_values", None)
        if isinstance(values, tuple) and len(values) == 2:
            set_session_cookies(response, values[0], values[1])
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; style-src 'self'; img-src 'self' https:; "
        "object-src 'none'; base-uri 'none'; form-action 'self'; frame-ancestors 'none'"
    )
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "same-origin"
    if response.headers.get("content-type", "").startswith("text/html"):
        response.headers["Cache-Control"] = "no-store"
    return response


async def buffer_limited_request_body(request: Request, limit: int) -> bool:
    chunks: list[bytes] = []
    total_size = 0
    async for chunk in request.stream():
        total_size += len(chunk)
        if total_size > limit:
            return False
        chunks.append(chunk)
    request._body = b"".join(chunks)
    return True


_AUTH_FORM_PATHS = {"/login", "/setup", "/recovery", "/settings/password", "/logout"}


@app.middleware("http")
async def enforce_auth_form_body_limit(
    request: Request,
    call_next: RequestResponseEndpoint,
) -> Response:
    if request.method == "POST" and request.url.path in _AUTH_FORM_PATHS:
        content_length = request.headers.get("content-length")
        if content_length is not None:
            try:
                declared_size = int(content_length)
            except ValueError:
                return JSONResponse(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    content={"detail": "Invalid Content-Length"},
                )
            if declared_size > settings.auth_form_body_limit_bytes:
                return JSONResponse(
                    status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                    content={"detail": "Authentication form is too large"},
                )
        if not await buffer_limited_request_body(request, settings.auth_form_body_limit_bytes):
            return JSONResponse(
                status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                content={"detail": "Authentication form is too large"},
            )
    return await call_next(request)


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
        if not await buffer_limited_request_body(request, settings.llm_request_body_limit_bytes):
            return JSONResponse(
                status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                content={"detail": "Request body too large"},
            )
    return await call_next(request)


app.include_router(api_router, prefix="/api")
app.include_router(web_router)


@app.get("/openapi-llm.json", include_in_schema=False)
async def llm_openapi(request: Request) -> dict[str, object]:
    server_url = settings.llm_api_server_url or str(request.base_url)
    return build_llm_openapi_schema(app, server_url=server_url)


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
