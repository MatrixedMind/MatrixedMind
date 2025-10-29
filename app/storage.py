import os
from typing import Any, Dict, List
from google.cloud import storage
from google.api_core import exceptions as gcs_exceptions
from fastapi import HTTPException
import time

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

def _create_section_index_if_missing(path: str, section: str) -> None:
    """Create section index file if it doesn't exist. Uses if_generation_match=0 for atomic creation."""
    blob = bucket.blob(path)
    try:
        # if_generation_match=0 ensures we only create if the blob doesn't exist
        blob.upload_from_string(
            f"# {section}\n\nNotes in this section:\n",
            if_generation_match=0
        )
    except gcs_exceptions.PreconditionFailed:
        # File already exists, which is fine
        pass

def _update_index_with_retry(path: str, item: str, is_project: bool, max_retries: int = 5) -> None:
    """
    Update an index file with retry logic using generation-based preconditions.
    
    Args:
        path: Path to the index file
        item: Section name (for project index) or title (for section index)
        is_project: True if updating project index, False if updating section index
        max_retries: Maximum number of retry attempts
    """
    for attempt in range(max_retries):
        try:
            blob = bucket.blob(path)
            blob.reload()  # Get current generation
            
            if blob.exists():
                # File exists, read current content and generation
                current_generation = blob.generation
                current = blob.download_as_text()
                
                # Prepare the link line based on type
                link_line = f"- [[{item}]]"
                
                # Check if update is needed
                if link_line in current:
                    return  # Already present, no update needed
                
                # Add the new link
                new_content = current.strip() + "\n" + link_line + "\n"
                
                # Upload with generation precondition to ensure atomicity
                blob.upload_from_string(new_content, if_generation_match=current_generation)
                return
            else:
                # File doesn't exist, create it
                if is_project:
                    # Extract project name from path for header
                    parts = path.split("/")
                    project_name = parts[-2] if len(parts) >= 2 else "Project"
                    initial_content = f"# {project_name}\n\nSections:\n- [[{item}]]\n"
                else:
                    # For section index, extract section name from path
                    parts = path.split("/")
                    section_name = parts[-2] if len(parts) >= 2 else "Section"
                    initial_content = f"# {section_name}\n\nNotes in this section:\n- [[{item}]]\n"
                
                # if_generation_match=0 ensures we only create if it doesn't exist
                blob.upload_from_string(initial_content, if_generation_match=0)
                return
                
        except gcs_exceptions.PreconditionFailed:
            # Someone else modified the file, retry
            if attempt < max_retries - 1:
                # Exponential backoff with jitter
                time.sleep(0.1 * (2 ** attempt))
                continue
            else:
                # Max retries exceeded
                raise HTTPException(
                    status_code=409,
                    detail=f"Failed to update index after {max_retries} attempts due to concurrent modifications"
                )

def ensure_index_files(project: str, section: str) -> None:
    # Create project-level _index.md if missing, and add section link if necessary
    _update_index_with_retry(_index_path(project), section, is_project=True)
    
    # Create section-level _index.md if missing
    _create_section_index_if_missing(_index_path(project, section), section)

def update_section_index(project: str, section: str, title: str) -> None:
    _update_index_with_retry(_index_path(project, section), title, is_project=False)

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
