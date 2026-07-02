import nh3
from fastapi import APIRouter, HTTPException, Request, Response
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from markdown_it import MarkdownIt

from app.dependencies import RecordRepoDep

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


@router.get("/", response_class=HTMLResponse)
async def index(request: Request, repo: RecordRepoDep) -> Response:
    # Just list some records from the default space for now
    records = repo.list_children("default", None)
    return templates.TemplateResponse(
        request=request, name="index.html", context={"title": "MatrixedMind", "records": records}
    )


@router.get("/{space}/{slug}", response_class=HTMLResponse)
async def view_record(request: Request, space: str, slug: str, repo: RecordRepoDep) -> Response:
    record = repo.get_by_slug(space, slug)
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")

    content_html = render_safe_markdown(record.body_markdown)

    return templates.TemplateResponse(
        request=request,
        name="record.html",
        context={"title": record.title, "record": record, "content_html": content_html},
    )
