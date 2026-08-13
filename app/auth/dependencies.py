from __future__ import annotations

import hashlib
import hmac
import secrets
import time
from collections import defaultdict, deque
from functools import lru_cache
from typing import Annotated

from fastapi import Depends, Header, HTTPException, Request, Response, status

from app.adapters.mongo.auth import MongoOwnerAuthRepository
from app.adapters.mongo.connection import MongoConnection
from app.auth.service import hash_opaque_secret, refresh_session, utc_now, valid_csrf
from app.domain.models import BrowserSession, PersonalAccessToken, PersonalAccessTokenScope, User
from app.domain.ports import OwnerAuthRepository, PersonalAccessTokenRepository
from app.settings import settings


def hash_personal_access_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def issue_personal_access_token() -> str:
    return secrets.token_urlsafe(32)


@lru_cache(maxsize=1)
def get_owner_auth_repository() -> OwnerAuthRepository:
    return MongoOwnerAuthRepository(
        MongoConnection.get_db(), ensure_indexes=settings.mongo_ensure_indexes
    )


def set_session_cookies(response: Response, raw_token: str, raw_csrf_token: str) -> None:
    secure = settings.app_env == "production"
    response.set_cookie(
        settings.session_cookie_name,
        raw_token,
        max_age=settings.session_inactivity_seconds,
        httponly=True,
        secure=secure,
        samesite="lax",
        path="/",
    )
    response.set_cookie(
        settings.csrf_cookie_name,
        raw_csrf_token,
        max_age=settings.session_inactivity_seconds,
        httponly=True,
        secure=secure,
        samesite="lax",
        path="/",
    )


def clear_session_cookies(response: Response) -> None:
    secure = settings.app_env == "production"
    response.delete_cookie(
        settings.session_cookie_name, httponly=True, secure=secure, samesite="lax", path="/"
    )
    response.delete_cookie(
        settings.csrf_cookie_name, httponly=True, secure=secure, samesite="lax", path="/"
    )


def authentication_required(request: Request) -> HTTPException:
    if request.url.path.startswith("/api/"):
        return HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required"
        )
    return HTTPException(
        status_code=status.HTTP_303_SEE_OTHER,
        detail="Authentication required",
        headers={"Location": "/login"},
    )


async def get_current_user(
    request: Request,
    repo: Annotated[OwnerAuthRepository, Depends(get_owner_auth_repository)],
    x_test_user_id: Annotated[str | None, Header()] = None,
) -> User:
    if settings.auth_mode == "test" and x_test_user_id:
        return User(id=x_test_user_id, display_name="Test User")
    if settings.auth_mode == "test":
        raise authentication_required(request)

    raw_token = request.cookies.get(settings.session_cookie_name)
    if raw_token is None:
        raise authentication_required(request)
    session = repo.get_session_by_hash(hash_opaque_secret(raw_token))
    if session is None:
        raise authentication_required(request)
    refreshed = refresh_session(
        session,
        raw_token,
        request.cookies.get(settings.csrf_cookie_name),
        settings,
    )
    if refreshed is None:
        repo.revoke_session(session.id, utc_now())
        raise authentication_required(request)
    try:
        persisted = repo.save_session(refreshed.session, previous_token_hash=session.token_hash)
    except RuntimeError as exc:
        raise authentication_required(request) from exc
    if persisted.revoked_at is not None:
        raise authentication_required(request)
    request.state.browser_session = persisted
    request.state.csrf_token = refreshed.raw_csrf_token
    request.state.session_cookie_values = (refreshed.raw_token, refreshed.raw_csrf_token)
    owner = repo.get_owner()
    if owner is None or owner.owner_id != persisted.owner_id:
        repo.revoke_session(persisted.id, utc_now())
        raise authentication_required(request)
    return User(id=owner.owner_id, display_name=owner.display_name)


CurrentUserDep = Annotated[User, Depends(get_current_user)]


def require_browser_csrf(request: Request, form_token: str | None) -> BrowserSession:
    if settings.auth_mode == "test" and request.headers.get("x-test-user-id"):
        now = utc_now()
        return BrowserSession(
            id="test-session",
            owner_id=request.headers["x-test-user-id"],
            token_hash="test-token-hash",
            csrf_token_hash="test-csrf-token-hash",
            created_at=now,
            last_seen_at=now,
            rotated_at=now,
            absolute_expires_at=now.replace(year=now.year + 1),
        )
    session = getattr(request.state, "browser_session", None)
    if not isinstance(session, BrowserSession) or not valid_csrf(
        session,
        request.cookies.get(settings.csrf_cookie_name),
        form_token,
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="CSRF validation failed")
    return session


def require_api_csrf(request: Request) -> BrowserSession:
    """Protect cookie-authenticated JSON writes from cross-site requests."""
    require_same_origin(request)
    return require_browser_csrf(request, request.headers.get("x-csrf-token"))


def require_same_origin(request: Request) -> None:
    if settings.auth_mode == "test" and request.headers.get("x-test-user-id"):
        return
    expected = str(request.base_url).rstrip("/")
    origin = request.headers.get("origin")
    if origin is not None:
        if not hmac.compare_digest(origin.rstrip("/"), expected):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Cross-origin form denied"
            )
        return
    referer = request.headers.get("referer")
    if referer is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Form origin required")
    referer_origin = referer.split("/", 3)[:3]
    if len(referer_origin) != 3 or not hmac.compare_digest("/".join(referer_origin), expected):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Cross-origin form denied"
        )


def bearer_token_from_request(request: Request) -> str:
    authorization = request.headers.get("authorization", "")
    scheme, _, value = authorization.partition(" ")
    if scheme.lower() != "bearer" or not value:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="LLM token required")
    return value


class PersonalAccessTokenRateLimiter:
    def __init__(self) -> None:
        self._requests: dict[str, deque[float]] = defaultdict(deque)

    def check(self, token_id: str) -> None:
        now = time.monotonic()
        cutoff = now - settings.llm_rate_limit_window_seconds
        requests = self._requests[token_id]
        while requests and requests[0] <= cutoff:
            requests.popleft()
        if len(requests) >= settings.llm_rate_limit_requests:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Rate limit exceeded"
            )
        requests.append(now)


personal_access_token_rate_limiter = PersonalAccessTokenRateLimiter()


def authenticate_personal_access_token(
    request: Request,
    token_repo: PersonalAccessTokenRepository,
    required_scope: PersonalAccessTokenScope,
) -> PersonalAccessToken:
    raw_token = bearer_token_from_request(request)
    token = token_repo.get_by_hash(hash_personal_access_token(raw_token))
    if token is None or token.is_revoked:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid LLM token")
    if required_scope not in token.scopes:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Token scope denied")
    personal_access_token_rate_limiter.check(token.id)
    return token
