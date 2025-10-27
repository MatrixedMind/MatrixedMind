import os
from typing import Any, Dict, List
from google.cloud import storage
from fastapi import HTTPException

BUCKET_NAME = os.environ.get("NOTES_BUCKET")
if not BUCKET_NAME:
    raise RuntimeError("NOTES_BUCKET env var missing")

client = storage.Client()
bucket = client.bucket(BUCKET_NAME)

def sanitize(segment: str) -> str:
    return "_".join(segment.strip().split())

def note_path(project: str, section: str, title: str) -> str:
    return f"notes/{sanitize(project)}/{sanitize(section)}/{sanitize(title)}.md"

def blob_exists(path: str) -> bool:
    return bucket.blob(path).exists()

def download_blob_text(path: str) -> str:
    blob = bucket.blob(path)
    return blob.download_as_text()

def upload_blob_text(path: str, content: str) -> None:
    blob = bucket.blob(path)
    blob.upload_from_string(content)

def get_note(project: str, section: str, title: str) -> str:
    # Kept for compatibility: takes project/section/title and returns content
    path = note_path(project, section, title)
    if not blob_exists(path):
        raise HTTPException(status_code=404, detail="note not found")
    return download_blob_text(path)

def save_note(path: str, content: str) -> None:
    blob = bucket.blob(path)
    blob.upload_from_string(content)

# Index helpers moved here so main can remain simple
def _index_path(project: str, section: str | None = None) -> str:
    if section is None:
        return f"notes/{sanitize(project)}/_index.md"
    else:
        return f"notes/{sanitize(project)}/{sanitize(section)}/_index.md"

def ensure_index_files(project: str, section: str) -> None:
    # Create project-level _index.md if missing, and add section link if necessary
    project_index_blob = bucket.blob(_index_path(project))
    if not project_index_blob.exists():
        project_index_blob.upload_from_string(
            f"# {project}\n\nSections:\n- [[{section}]]\n"
        )
    else:
        current = project_index_blob.download_as_text()
        link_line = f"- [[{section}]]"
        if link_line not in current:
            current = current.strip() + "\n" + link_line + "\n"
            project_index_blob.upload_from_string(current)

    # Create section-level _index.md if missing
    section_index_blob = bucket.blob(_index_path(project, section))
    if not section_index_blob.exists():
        section_index_blob.upload_from_string(
            f"# {section}\n\nNotes in this section:\n"
        )

def update_section_index(project: str, section: str, title: str) -> None:
    blob = bucket.blob(_index_path(project, section))
    if not blob.exists():
        blob.upload_from_string(f"# {section}\n\nNotes in this section:\n- [[{title}]]\n")
        return

    current = blob.download_as_text()
    link_line = f"- [[{title}]]"
    if link_line not in current:
        current = current.strip() + "\n" + link_line + "\n"
        blob.upload_from_string(current)

def list_tree(prefix: str = "notes/") -> List[Dict[str, Any]]:
    # Walk the bucket under the given prefix and return the same nested structure
    blobs = bucket.list_blobs(prefix=prefix)
    tree = {}

    for b in blobs:
        if b.name.endswith("/"):
            continue
        parts = b.name.split("/")
        if len(parts) != 4:
            continue
        _, project, section, filename = parts
        if filename == "_index.md":
            continue
        title = filename[:-3] if filename.endswith(".md") else filename

        proj = tree.setdefault(project, {})
        sec = proj.setdefault(section, [])
        if title not in sec:
            sec.append(title)

    projects_out = []
    for project, sections in tree.items():
        sections_out = []
        for section, notes in sections.items():
            sections_out.append({
                "name": section,
                "notes": sorted(notes),
            })
        projects_out.append({
            "name": project,
            "sections": sorted(sections_out, key=lambda s: s["name"].lower()),
        })

    projects_out = sorted(projects_out, key=lambda p: p["name"].lower())
    return projects_out
