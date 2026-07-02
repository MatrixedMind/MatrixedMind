from typing import Any
from urllib.parse import parse_qs

import nh3
from fastapi import APIRouter, HTTPException, Request, Response, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from markdown_it import MarkdownIt
from pydantic import ValidationError

from app.api.schemas.records import RecordCreate, RecordUpdate
from app.dependencies import RecordRepoDep
from app.domain.models import Record

router = APIRouter()
templates = Jinja2Templates(directory="app/web/templates")
md = MarkdownIt()

ALLOWED_HTML_TAGS: set[str] = {
    "a",
    "blockquote",
    "br",
    "code",
    "em",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "hr",
    "li",
    "ol",
    "p",
    "pre",
    "strong",
    "ul",
}

ALLOWED_HTML_ATTRIBUTES: dict[str, set[str]] = {
    "a": {"href", "title"},
}

ALLOWED_HTML_SCHEMES: set[str] = {"http", "https", "mailto"}


def render_safe_markdown(markdown_text: str) -> str:
    rendered_html = md.render(markdown_text)
    return nh3.clean(
        rendered_html,
        tags=ALLOWED_HTML_TAGS,
        attributes=ALLOWED_HTML_ATTRIBUTES,
        url_schemes=ALLOWED_HTML_SCHEMES,
    )


async def parse_urlencoded_form(request: Request) -> dict[str, str]:
    body = (await request.body()).decode()
    parsed = parse_qs(body, keep_blank_values=True)
    return {key: values[-1] for key, values in parsed.items()}


def parse_tags(tags_value: str) -> list[str]:
    return [tag.strip() for tag in tags_value.split(",") if tag.strip()]


def editor_context(
    *,
    title: str,
    heading: str,
    form_action: str,
    record: Record | dict[str, Any] | None,
    tags_value: str,
    error: str | None = None,
) -> dict[str, object]:
    return {
        "title": title,
        "heading": heading,
        "record": record,
        "form_action": form_action,
        "tags_value": tags_value,
        "error": error,
    }


def render_editor(
    request: Request,
    *,
    title: str,
    heading: str,
    form_action: str,
    record: Record | dict[str, Any] | None,
    tags_value: str,
    error: str | None = None,
    status_code: int = status.HTTP_200_OK,
) -> Response:
    return templates.TemplateResponse(
        request=request,
        name="editor.html",
        context=editor_context(
            title=title,
            heading=heading,
            form_action=form_action,
            record=record,
            tags_value=tags_value,
            error=error,
        ),
        status_code=status_code,
    )


def detail_redirect(record: Record) -> RedirectResponse:
    return RedirectResponse(
        url=f"/{record.space}/{record.slug}",
        status_code=status.HTTP_303_SEE_OTHER,
    )


@router.get("/", response_class=HTMLResponse)
def index(request: Request, repo: RecordRepoDep) -> Response:
    # Just list some records from the default space for now
    records = repo.list_children("default", None)
    return templates.TemplateResponse(
        request=request, name="index.html", context={"title": "MatrixedMind", "records": records}
    )


@router.get("/records/new", response_class=HTMLResponse)
def new_record(request: Request) -> Response:
    return render_editor(
        request=request,
        title="New Page",
        heading="New Page",
        record=None,
        form_action="/records/new",
        tags_value="",
    )


@router.post("/records/new", response_class=HTMLResponse)
async def create_record_from_form(request: Request, repo: RecordRepoDep) -> Response:
    form_data = await parse_urlencoded_form(request)
    record_values: dict[str, object] = {
        "space": form_data.get("space", ""),
        "slug": form_data.get("slug", ""),
        "title": form_data.get("title", ""),
        "body_markdown": form_data.get("body_markdown", ""),
        "tags": parse_tags(form_data.get("tags", "")),
    }

    try:
        record_in = RecordCreate.model_validate(record_values)
    except ValidationError as exc:
        return render_editor(
            request,
            title="New Page",
            heading="New Page",
            record=record_values,
            form_action="/records/new",
            tags_value=form_data.get("tags", ""),
            error=str(exc),
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    if repo.get_by_slug(record_in.space, record_in.slug):
        return render_editor(
            request,
            title="New Page",
            heading="New Page",
            record=record_values,
            form_action="/records/new",
            tags_value=form_data.get("tags", ""),
            error=(
                f"Record with slug '{record_in.slug}' already exists in space '{record_in.space}'"
            ),
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    record = repo.create(Record(**record_in.model_dump()))
    return detail_redirect(record)


@router.get("/{space}/{slug}/edit", response_class=HTMLResponse)
def edit_record(request: Request, space: str, slug: str, repo: RecordRepoDep) -> Response:
    record = repo.get_by_slug(space, slug)
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")

    return render_editor(
        request=request,
        title=f"Edit {record.title}",
        heading=f"Edit {record.title}",
        record=record,
        form_action=f"/{record.space}/{record.slug}/edit",
        tags_value=", ".join(record.tags),
    )


@router.post("/{space}/{slug}/edit", response_class=HTMLResponse)
async def update_record_from_form(
    request: Request,
    space: str,
    slug: str,
    repo: RecordRepoDep,
) -> Response:
    existing = repo.get_by_slug(space, slug)
    if not existing:
        raise HTTPException(status_code=404, detail="Record not found")
    if existing.id is None:
        raise HTTPException(
            status_code=400,
            detail="Existing record cannot be updated without an id",
        )

    form_data = await parse_urlencoded_form(request)
    update_values: dict[str, object] = {
        "space": form_data.get("space", ""),
        "slug": form_data.get("slug", ""),
        "title": form_data.get("title", ""),
        "body_markdown": form_data.get("body_markdown", ""),
        "tags": parse_tags(form_data.get("tags", "")),
    }

    try:
        record_in = RecordUpdate.model_validate(update_values)
    except ValidationError as exc:
        return render_editor(
            request,
            title=f"Edit {existing.title}",
            heading=f"Edit {existing.title}",
            record=update_values,
            form_action=f"/{space}/{slug}/edit",
            tags_value=form_data.get("tags", ""),
            error=str(exc),
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    next_space = record_in.space or existing.space
    next_slug = record_in.slug or existing.slug
    duplicate = repo.get_by_slug(next_space, next_slug)
    if duplicate is not None and duplicate.id != existing.id:
        return render_editor(
            request,
            title=f"Edit {existing.title}",
            heading=f"Edit {existing.title}",
            record=update_values,
            form_action=f"/{space}/{slug}/edit",
            tags_value=form_data.get("tags", ""),
            error=f"Record with slug '{next_slug}' already exists in space '{next_space}'",
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    updated = existing.model_copy(update=record_in.model_dump(exclude_unset=True))
    try:
        record = repo.update(existing.id, updated)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Record not found") from exc
    except ValueError as exc:
        return render_editor(
            request,
            title=f"Edit {existing.title}",
            heading=f"Edit {existing.title}",
            record=update_values,
            form_action=f"/{space}/{slug}/edit",
            tags_value=form_data.get("tags", ""),
            error=str(exc),
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    return detail_redirect(record)


@router.get("/{space}/{slug}", response_class=HTMLResponse)
def view_record(request: Request, space: str, slug: str, repo: RecordRepoDep) -> Response:
    record = repo.get_by_slug(space, slug)
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")

    content_html = render_safe_markdown(record.body_markdown)

    return templates.TemplateResponse(
        request=request,
        name="record.html",
        context={"title": record.title, "record": record, "content_html": content_html},
    )
