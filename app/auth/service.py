from __future__ import annotations

import hashlib
import hmac
import secrets
import time
from collections import defaultdict, deque
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from threading import RLock

from argon2 import PasswordHasher, Type
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

from app.domain.models import (
    BrowserSession,
    OneTimeCredential,
    OneTimeCredentialPurpose,
)
from app.domain.ports import OwnerAuthRepository
from app.settings import Settings

PASSWORD_MIN_LENGTH = 12
PASSWORD_MAX_LENGTH = 1024
_password_hasher = PasswordHasher(type=Type.ID)


@dataclass(frozen=True)
class IssuedSession:
    session: BrowserSession
    raw_token: str
    raw_csrf_token: str


class AuthenticationAttemptLimiter:
    """Bound credential-form work per process and remote address."""

    def __init__(self) -> None:
        self._attempts: dict[str, deque[float]] = defaultdict(deque)
        self._lock = RLock()

    def check(self, key: str, configured: Settings) -> bool:
        now = time.monotonic()
        cutoff = now - configured.auth_attempt_window_seconds
        with self._lock:
            attempts = self._attempts[key]
            while attempts and attempts[0] <= cutoff:
                attempts.popleft()
            if len(attempts) >= configured.auth_attempt_limit:
                return False
            attempts.append(now)
            return True

    def reset(self, key: str) -> None:
        with self._lock:
            self._attempts.pop(key, None)

    def clear(self) -> None:
        with self._lock:
            self._attempts.clear()


authentication_attempt_limiter = AuthenticationAttemptLimiter()


def utc_now() -> datetime:
    return datetime.now(UTC)


def hash_opaque_secret(raw_secret: str) -> str:
    return hashlib.sha256(raw_secret.encode("utf-8")).hexdigest()


def issue_opaque_secret() -> str:
    return secrets.token_urlsafe(32)


def validate_password(password: str) -> str:
    if "\x00" in password:
        raise ValueError("password must not contain a null byte")
    if len(password) < PASSWORD_MIN_LENGTH:
        raise ValueError(f"password must contain at least {PASSWORD_MIN_LENGTH} characters")
    if len(password) > PASSWORD_MAX_LENGTH:
        raise ValueError(f"password must contain at most {PASSWORD_MAX_LENGTH} characters")
    if not password.strip():
        raise ValueError("password must not be blank")
    return password


def hash_password(password: str) -> str:
    return _password_hasher.hash(validate_password(password))


def verify_password(password_hash: str, candidate: str) -> bool:
    if "\x00" in candidate or len(candidate) > PASSWORD_MAX_LENGTH:
        return False
    try:
        return _password_hasher.verify(password_hash, candidate)
    except (InvalidHashError, VerificationError, VerifyMismatchError):
        return False


def password_hash_needs_rehash(password_hash: str) -> bool:
    try:
        return _password_hasher.check_needs_rehash(password_hash)
    except InvalidHashError:
        return True


def issue_session(
    owner_id: str, configured: Settings, *, now: datetime | None = None
) -> IssuedSession:
    issued_at = now or utc_now()
    raw_token = issue_opaque_secret()
    raw_csrf_token = issue_opaque_secret()
    session = BrowserSession(
        id=secrets.token_urlsafe(18),
        owner_id=owner_id,
        token_hash=hash_opaque_secret(raw_token),
        csrf_token_hash=hash_opaque_secret(raw_csrf_token),
        created_at=issued_at,
        last_seen_at=issued_at,
        rotated_at=issued_at,
        absolute_expires_at=issued_at + timedelta(seconds=configured.session_absolute_seconds),
    )
    return IssuedSession(session=session, raw_token=raw_token, raw_csrf_token=raw_csrf_token)


def refresh_session(
    session: BrowserSession,
    raw_token: str,
    raw_csrf_token: str | None,
    configured: Settings,
    *,
    now: datetime | None = None,
) -> IssuedSession | None:
    checked_at = now or utc_now()
    inactive_at = session.last_seen_at + timedelta(seconds=configured.session_inactivity_seconds)
    if (
        session.revoked_at is not None
        or checked_at >= inactive_at
        or checked_at >= session.absolute_expires_at
    ):
        return None

    rotate = checked_at >= session.rotated_at + timedelta(
        seconds=configured.session_rotation_seconds
    )
    csrf_matches = raw_csrf_token is not None and hmac.compare_digest(
        session.csrf_token_hash,
        hash_opaque_secret(raw_csrf_token),
    )
    next_token = issue_opaque_secret() if rotate else raw_token
    next_csrf = (
        issue_opaque_secret()
        if rotate or not csrf_matches or raw_csrf_token is None
        else raw_csrf_token
    )
    refreshed = session.model_copy(
        update={
            "token_hash": hash_opaque_secret(next_token),
            "csrf_token_hash": hash_opaque_secret(next_csrf),
            "last_seen_at": checked_at,
            "rotated_at": checked_at if rotate else session.rotated_at,
        }
    )
    return IssuedSession(session=refreshed, raw_token=next_token, raw_csrf_token=next_csrf)


def valid_csrf(session: BrowserSession, cookie_token: str | None, form_token: str | None) -> bool:
    if cookie_token is None or form_token is None:
        return False
    cookie_matches_form = hmac.compare_digest(cookie_token, form_token)
    cookie_matches_session = hmac.compare_digest(
        hash_opaque_secret(cookie_token), session.csrf_token_hash
    )
    return cookie_matches_form and cookie_matches_session


def issue_operator_credential(
    repo: OwnerAuthRepository,
    purpose: OneTimeCredentialPurpose,
    configured: Settings,
    *,
    now: datetime | None = None,
) -> str:
    issued_at = now or utc_now()
    owner_exists = repo.get_owner() is not None
    if purpose == "bootstrap" and owner_exists:
        raise ValueError("bootstrap is unavailable after owner setup")
    if purpose == "recovery" and not owner_exists:
        raise ValueError("recovery is unavailable before owner setup")
    raw_token = issue_opaque_secret()
    repo.save_one_time_credential(
        OneTimeCredential(
            id=secrets.token_urlsafe(18),
            purpose=purpose,
            token_hash=hash_opaque_secret(raw_token),
            created_at=issued_at,
            expires_at=issued_at + timedelta(seconds=configured.operator_credential_ttl_seconds),
        )
    )
    return raw_token
