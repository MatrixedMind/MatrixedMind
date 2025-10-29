import os
import time
import re
from typing import Any, Dict, List
from google.cloud import storage
from google.api_core import exceptions
from fastapi import HTTPException

BUCKET_NAME = os.environ.get("NOTES_BUCKET")
if not BUCKET_NAME:
    raise RuntimeError("NOTES_BUCKET env var missing")

client = storage.Client()
bucket = client.bucket(BUCKET_NAME)

def sanitize(segment: str) -> str:
    r"""
    Sanitize a segment for use in GCS object paths.
    
    Replaces whitespace with underscores and removes/replaces characters
    that could be problematic in GCS paths, including:
    - Path separators (/, \)
    - Control characters
    - Special characters that could cause issues
    
    This prevents path traversal attacks and unexpected storage behavior.
    """
    # First, strip leading/trailing whitespace
    segment = segment.strip()
    
    # Replace internal whitespace with underscores
    segment = "_".join(segment.split())
    
    # Remove control characters (ASCII 0-31 and 127)
    segment = "".join(char for char in segment if ord(char) >= 32 and ord(char) != 127)
    
    # Replace path separators and other problematic characters with underscores
    # This includes: / \ : * ? " < > | and dots (to prevent hidden files and path traversal)
    problematic_chars = r'[/\\:*?"<>|\.]'
    segment = re.sub(problematic_chars, "_", segment)
    
    # Remove leading/trailing underscores that may result from sanitization
    segment = segment.strip("_")
    
    # If the segment is empty after sanitization, return a safe default
    if not segment:
        segment = "unnamed"
    
    return segment

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

# Index helpers moved here so main can remain simple
def _index_path(project: str, section: str | None = None) -> str:
    if section is None:
        return f"notes/{sanitize(project)}/_index.md"
    else:
        return f"notes/{sanitize(project)}/{sanitize(section)}/_index.md"

def _retry_on_conflict(func, max_retries: int = 5):
    """Retry a function that may encounter precondition failures due to concurrent updates."""
    for attempt in range(max_retries):
        try:
            return func()
        except (exceptions.PreconditionFailed, exceptions.NotFound):
            if attempt == max_retries - 1:
                raise
            # Exponential backoff: 0.1s, 0.2s, 0.4s, 0.8s
            time.sleep(0.1 * (2 ** attempt))

def ensure_index_files(project: str, section: str) -> None:
    """Ensure project and section index files exist with atomic operations to prevent race conditions."""
    
    # Update project-level index
    def _update_project_index():
        project_path = _index_path(project)
        blob = bucket.blob(project_path)
        
        # Try to create first - this will fail if blob already exists
        try:
            blob.upload_from_string(
                f"# {project}\n\nSections:\n- [[{section}]]\n",
                if_generation_match=0
            )
            return  # Successfully created, we're done
        except exceptions.PreconditionFailed:
            # Blob already exists, need to update it
            pass
        
        # Blob exists, reload metadata to capture current generation before downloading
        blob.reload()
        generation = blob.generation
        if generation is None:
            raise exceptions.PreconditionFailed("Blob generation unavailable for conditional update")

        current = blob.download_as_text(if_generation_match=generation)
        link_line = f"- [[{section}]]"

        if link_line in current:
            # Already present, nothing to do
            return
        
        # Update content and upload only if generation hasn't changed
        new_content = current.strip() + "\n" + link_line + "\n"
        blob.upload_from_string(new_content, if_generation_match=generation)
    
    _retry_on_conflict(_update_project_index)
    
    # Create section-level index if it doesn't exist
    section_path = _index_path(project, section)
    blob = bucket.blob(section_path)
    
    # Try to create - if it fails, blob already exists (which is fine)
    try:
        blob.upload_from_string(
            f"# {section}\n\nNotes in this section:\n",
            if_generation_match=0
        )
    except exceptions.PreconditionFailed:
        # Blob already exists from another process, no action needed
        pass

def update_section_index(project: str, section: str, title: str) -> None:
    """Update section index with atomic operations to prevent race conditions."""
    path = _index_path(project, section)
    
    def _update():
        blob = bucket.blob(path)
        
        # Try to create first - this will fail if blob already exists
        try:
            blob.upload_from_string(
                f"# {section}\n\nNotes in this section:\n- [[{title}]]\n",
                if_generation_match=0
            )
            return  # Successfully created, we're done
        except exceptions.PreconditionFailed:
            # Blob already exists, need to update it
            pass
        
        # Blob exists, reload metadata to capture current generation before downloading
        blob.reload()
        generation = blob.generation
        if generation is None:
            raise exceptions.PreconditionFailed("Blob generation unavailable for conditional update")

        current = blob.download_as_text(if_generation_match=generation)
        link_line = f"- [[{title}]]"

        if link_line in current:
            # Already present, nothing to do
            return
        
        # Update content and upload only if generation hasn't changed
        new_content = current.strip() + "\n" + link_line + "\n"
        blob.upload_from_string(new_content, if_generation_match=generation)
    
    _retry_on_conflict(_update)

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
