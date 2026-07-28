from __future__ import annotations

import hashlib
import secrets
import time
from collections import defaultdict, deque
from typing import Annotated

from fastapi import Depends, Header, HTTPException, Request, status

from app.domain.models import LlmApiToken, LlmTokenScope, User
from app.domain.ports import LlmTokenRepository
from app.settings import settings


def hash_llm_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def issue_llm_token() -> str:
    return secrets.token_urlsafe(32)


async def get_current_user(
    x_test_user_id: Annotated[str | None, Header()] = None,
) -> User:
    if settings.auth_mode == "dev":
        return User(id="dev-user", display_name="Dev User")
    if settings.auth_mode == "test" and x_test_user_id:
        return User(id=x_test_user_id, display_name="Test User")
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")


CurrentUserDep = Annotated[User, Depends(get_current_user)]


def bearer_token_from_request(request: Request) -> str:
    authorization = request.headers.get("authorization", "")
    scheme, _, value = authorization.partition(" ")
    if scheme.lower() != "bearer" or not value:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="LLM token required")
    return value


class LlmRateLimiter:
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


llm_rate_limiter = LlmRateLimiter()


def authenticate_llm_token(
    request: Request,
    token_repo: LlmTokenRepository,
    required_scope: LlmTokenScope,
) -> LlmApiToken:
    raw_token = bearer_token_from_request(request)
    token = token_repo.get_by_hash(hash_llm_token(raw_token))
    if token is None or token.is_revoked:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid LLM token")
    if required_scope not in token.scopes:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Token scope denied")
    llm_rate_limiter.check(token.id)
    return token
