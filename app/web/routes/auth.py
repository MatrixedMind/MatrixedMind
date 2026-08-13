from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated
from urllib.parse import parse_qs

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.auth.dependencies import (
    CurrentUserDep,
    clear_session_cookies,
    get_owner_auth_repository,
    require_browser_csrf,
    require_same_origin,
    set_session_cookies,
)
from app.auth.service import (
    authentication_attempt_limiter,
    hash_opaque_secret,
    hash_password,
    issue_session,
    validate_password,
    verify_password,
)
from app.domain.models import OwnerCredential
from app.domain.ports import OwnerAuthRepository
from app.settings import settings

router = APIRouter()
templates = Jinja2Templates(directory="app/web/templates")
templates.env.globals["source_offer_url"] = settings.source_offer_url
OwnerAuthRepoDep = Annotated[OwnerAuthRepository, Depends(get_owner_auth_repository)]


def attempt_key(request: Request, purpose: str) -> str:
    client_host = request.client.host if request.client is not None else "unknown"
    return f"{purpose}:{client_host}"


def require_attempt_budget(request: Request, purpose: str) -> str:
    key = attempt_key(request, purpose)
    if not authentication_attempt_limiter.check(key, settings):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many authentication attempts; try again later",
        )
    return key


async def parse_form(request: Request) -> dict[str, str]:
    try:
        body = (await request.body()).decode("utf-8")
    except UnicodeDecodeError as exc:
        raise HTTPException(status_code=400, detail="Invalid form encoding") from exc
    parsed = parse_qs(body, keep_blank_values=True)
    return {key: values[-1] for key, values in parsed.items()}


def auth_response(
    request: Request,
    template: str,
    *,
    title: str,
    error: str | None = None,
    status_code: int = status.HTTP_200_OK,
) -> Response:
    return templates.TemplateResponse(
        request=request,
        name=template,
        context={
            "title": title,
            "error": error,
            "robots_content": "noindex,nofollow,noarchive",
        },
        status_code=status_code,
    )


def passwords_from_form(form: dict[str, str]) -> str:
    password = form.get("password", "")
    if password != form.get("password_confirmation", ""):
        raise ValueError("password confirmation does not match")
    return validate_password(password)


@router.get("/login", response_class=HTMLResponse)
def login_form(request: Request) -> Response:
    return auth_response(request, "login.html", title="Sign in to MatrixedMind")


@router.post("/login", response_class=HTMLResponse)
async def login(request: Request, repo: OwnerAuthRepoDep) -> Response:
    require_same_origin(request)
    limiter_key = require_attempt_budget(request, "login")
    form = await parse_form(request)
    owner = repo.get_owner()
    if owner is None or not verify_password(owner.password_hash, form.get("password", "")):
        return auth_response(
            request,
            "login.html",
            title="Sign in to MatrixedMind",
            error="The password was not accepted.",
            status_code=status.HTTP_401_UNAUTHORIZED,
        )
    issued = issue_session(owner.owner_id, settings)
    repo.save_session(issued.session)
    authentication_attempt_limiter.reset(limiter_key)
    response = RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    set_session_cookies(response, issued.raw_token, issued.raw_csrf_token)
    return response


@router.get("/setup", response_class=HTMLResponse)
def setup_form(request: Request, repo: OwnerAuthRepoDep) -> Response:
    if repo.get_owner() is not None:
        return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
    return auth_response(request, "setup.html", title="Set up this MatrixedMind Instance")


@router.post("/setup", response_class=HTMLResponse)
async def setup(request: Request, repo: OwnerAuthRepoDep) -> Response:
    require_same_origin(request)
    limiter_key = require_attempt_budget(request, "setup")
    if repo.get_owner() is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Owner setup is complete")
    form = await parse_form(request)
    try:
        password = passwords_from_form(form)
        display_name = form.get("display_name", "").strip()
        credential = OwnerCredential(
            owner_id="owner",
            display_name=display_name,
            password_hash=hash_password(password),
        )
    except ValueError as exc:
        return auth_response(
            request,
            "setup.html",
            title="Set up this MatrixedMind Instance",
            error=str(exc),
            status_code=status.HTTP_400_BAD_REQUEST,
        )
    created = repo.bootstrap_owner(
        credential,
        hash_opaque_secret(form.get("operator_credential", "")),
        datetime.now(UTC),
    )
    if not created:
        return auth_response(
            request,
            "setup.html",
            title="Set up this MatrixedMind Instance",
            error="The bootstrap credential is invalid, expired, or already used.",
            status_code=status.HTTP_403_FORBIDDEN,
        )
    authentication_attempt_limiter.reset(limiter_key)
    issued = issue_session(credential.owner_id, settings)
    repo.save_session(issued.session)
    response = RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    set_session_cookies(response, issued.raw_token, issued.raw_csrf_token)
    return response


@router.get("/recovery", response_class=HTMLResponse)
def recovery_form(request: Request, repo: OwnerAuthRepoDep) -> Response:
    if repo.get_owner() is None:
        return RedirectResponse(url="/setup", status_code=status.HTTP_303_SEE_OTHER)
    return auth_response(request, "recovery.html", title="Recover the MatrixedMind owner")


@router.post("/recovery", response_class=HTMLResponse)
async def recovery(request: Request, repo: OwnerAuthRepoDep) -> Response:
    require_same_origin(request)
    limiter_key = require_attempt_budget(request, "recovery")
    owner = repo.get_owner()
    if owner is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Owner setup is incomplete"
        )
    form = await parse_form(request)
    try:
        password = passwords_from_form(form)
        password_hash = hash_password(password)
    except ValueError as exc:
        return auth_response(
            request,
            "recovery.html",
            title="Recover the MatrixedMind owner",
            error=str(exc),
            status_code=status.HTTP_400_BAD_REQUEST,
        )
    changed_at = datetime.now(UTC)
    recovered = repo.recover_owner(
        owner.model_copy(
            update={"password_hash": password_hash, "password_changed_at": changed_at}
        ),
        hash_opaque_secret(form.get("operator_credential", "")),
        changed_at,
    )
    if not recovered:
        return auth_response(
            request,
            "recovery.html",
            title="Recover the MatrixedMind owner",
            error="The recovery credential is invalid, expired, or already used.",
            status_code=status.HTTP_403_FORBIDDEN,
        )
    authentication_attempt_limiter.reset(limiter_key)
    response = RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
    clear_session_cookies(response)
    return response


@router.get("/settings/password", response_class=HTMLResponse)
def password_form(request: Request, _user: CurrentUserDep) -> Response:
    return auth_response(request, "password.html", title="Change owner password")


@router.post("/settings/password", response_class=HTMLResponse)
async def change_password(
    request: Request,
    repo: OwnerAuthRepoDep,
    user: CurrentUserDep,
) -> Response:
    require_same_origin(request)
    form = await parse_form(request)
    session = require_browser_csrf(request, form.get("csrf_token"))
    owner = repo.get_owner()
    if owner is None or owner.owner_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required"
        )
    if not verify_password(owner.password_hash, form.get("current_password", "")):
        return auth_response(
            request,
            "password.html",
            title="Change owner password",
            error="The current password was not accepted.",
            status_code=status.HTTP_400_BAD_REQUEST,
        )
    try:
        password = passwords_from_form(form)
        password_hash = hash_password(password)
    except ValueError as exc:
        return auth_response(
            request,
            "password.html",
            title="Change owner password",
            error=str(exc),
            status_code=status.HTTP_400_BAD_REQUEST,
        )
    changed_at = datetime.now(UTC)
    changed = repo.change_password(
        owner.model_copy(
            update={"password_hash": password_hash, "password_changed_at": changed_at}
        ),
        session.id,
        owner.password_hash,
        changed_at,
    )
    if not changed:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Owner credential or session changed; sign in and try again",
        )
    return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/logout")
async def logout(request: Request, repo: OwnerAuthRepoDep, _user: CurrentUserDep) -> Response:
    require_same_origin(request)
    form = await parse_form(request)
    session = require_browser_csrf(request, form.get("csrf_token"))
    repo.revoke_session(session.id, datetime.now(UTC))
    response = RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
    clear_session_cookies(response)
    request.state.suppress_session_refresh = True
    return response
