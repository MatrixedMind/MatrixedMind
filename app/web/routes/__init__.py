from fastapi import APIRouter, HTTPException, Request, Response
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from markdown_it import MarkdownIt

from app.dependencies import RecordRepoDep

router = APIRouter()
templates = Jinja2Templates(directory="app/web/templates")
md = MarkdownIt()


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

    content_html = md.render(record.body_markdown)

    return templates.TemplateResponse(
        request=request,
        name="record.html",
        context={"title": record.title, "record": record, "content_html": content_html},
    )
