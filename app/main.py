from fastapi import FastAPI, Header, HTTPException, Query
from .models import NotePayload
from datetime import datetime, timezone
import os
import secrets

from typing import Any, Dict, Optional

from . import storage

app = FastAPI(title="Personal Notes API", version="v1")

NOTES_API_KEY = os.environ.get("NOTES_API_KEY")
NOTES_BUCKET = os.environ.get("NOTES_BUCKET")

if not NOTES_API_KEY:
    raise RuntimeError("NOTES_API_KEY env var not set")
if not NOTES_BUCKET:
    raise RuntimeError("NOTES_BUCKET env var not set")


def _timestamp_header() -> str:
    # Example: ## 2025-10-24 12:34:56
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    return f"\n## {now}\n"


# Truncation indicator constants
_TRUNCATE_EXISTING = "...(existing)\n"
_TRUNCATE_NEW_ENTRY = "\n...(new entry)\n"
_TRUNCATE_ELLIPSIS = "\n...\n"


def _truncate_content(content: str, mode: str, existing_content: Optional[str] = None, char_limit: int = 10000) -> str:
    """
    Truncate content intelligently based on size and mode.
    
    Args:
        content: The full content to potentially truncate
        mode: Either "replace" or "append"
        existing_content: The previous content (only relevant for append mode)
        char_limit: Maximum characters before truncation (default 10000)
    
    Returns:
        Original content if within limit, otherwise intelligently truncated content
    """
    # If content is within limit, return as-is
    if len(content) <= char_limit:
        return content
    
    # Content exceeds limit, truncate intelligently based on mode
    if mode == "replace":
        # For replace mode: first half + "..." + last half
        half_limit = char_limit // 2
        truncated = (
            content[:half_limit] +
            _TRUNCATE_ELLIPSIS +
            content[-half_limit:]
        )
        return truncated
    
    else:  # append mode
        # For append mode, we want to show context from both old and new content
        # Strategy: 
        # - Show last 20% of char_limit from existing content
        # - Show first 40% from new content
        # - Show last 40% from new content
        
        if existing_content:
            # Find where the new content starts
            # Note: existing_content was stripped before appending, so we need to account for that
            existing_stripped = existing_content.rstrip()
            # The new content includes everything after the stripped existing content
            start_pos = len(existing_stripped)
            new_content = content[start_pos:]
            
            # Calculate limits
            existing_chars = int(char_limit * 0.2)
            new_first_chars = int(char_limit * 0.4)
            new_last_chars = int(char_limit * 0.4)
            
            # Build truncated version
            truncated_existing = existing_content[-existing_chars:] if existing_chars < len(existing_content) else existing_content
            has_truncated_existing = existing_chars < len(existing_content)
            prefix = _TRUNCATE_EXISTING if has_truncated_existing else ""
            
            if len(new_content) <= (new_first_chars + new_last_chars):
                # New content fits in the allocation
                truncated = prefix + truncated_existing + new_content
            else:
                # New content needs truncation too
                truncated = (
                    prefix +
                    truncated_existing +
                    _TRUNCATE_NEW_ENTRY +
                    new_content[:new_first_chars] +
                    _TRUNCATE_ELLIPSIS +
                    new_content[-new_last_chars:]
                )
            
            return truncated
        else:
            # No existing content, treat like replace mode
            half_limit = char_limit // 2
            return (
                content[:half_limit] +
                _TRUNCATE_ELLIPSIS +
                content[-half_limit:]
            )


@app.get("/ping")
def ping() -> Dict[str, str]:
    """
    Public health check endpoint for monitoring and load balancer probes.
    
    This endpoint is intentionally unauthenticated to allow external tools
    (monitoring systems, load balancers, Cloud Run health checks) to verify
    service reachability without requiring API credentials.
    
    Security note: Returns only a minimal status response with no sensitive
    information about the service internals, configuration, or data.
    """
    return {"status": "ok"}


@app.post("/api/v1/notes")
def create_or_update_note(
    payload: NotePayload,
    x_notes_key: Optional[str] = Header(None),
) -> Dict[str, Any]:
    if not x_notes_key or not secrets.compare_digest(x_notes_key, NOTES_API_KEY):
        raise HTTPException(status_code=401, detail="unauthorized")

    blob_path = storage.note_path(payload.project, payload.section, payload.title)

    existing_content = None
    if payload.mode == "replace" or not storage.blob_exists(blob_path):
        new_content = f"# {payload.title}\n" + _timestamp_header() + payload.body.strip() + "\n"
    else:
        existing_content = storage.download_blob_text(blob_path)
        new_content = existing_content.rstrip() + _timestamp_header() + payload.body.strip() + "\n"

    storage.upload_blob_text(blob_path, new_content)

    # update index helpers in storage module
    storage.ensure_index_files(payload.project, payload.section)
    storage.update_section_index(payload.project, payload.section, payload.title)

    # Truncate content for response if needed
    response_content = _truncate_content(new_content, payload.mode, existing_content)

    return {
        "status": "ok",
        "path": blob_path,
        "content": response_content,
    }


@app.get("/api/v1/notes")
def get_note(
    project: str = Query(...),
    section: str = Query(...),
    title: str = Query(...),
    x_notes_key: Optional[str] = Header(None),
) -> Dict[str, Any]:
    if not x_notes_key or not secrets.compare_digest(x_notes_key, NOTES_API_KEY):
        raise HTTPException(status_code=401, detail="unauthorized")

    blob_path = storage.note_path(project, section, title)
    if not storage.blob_exists(blob_path):
        raise HTTPException(status_code=404, detail="note not found")

    content = storage.download_blob_text(blob_path)
    # Truncate content for response if needed (use "replace" mode for GET)
    response_content = _truncate_content(content, "replace")

    return {
        "status": "ok",
        "path": blob_path,
        "content": response_content,
    }


@app.get("/api/v1/index")
def get_index(
    x_notes_key: Optional[str] = Header(None),
) -> Dict[str, Any]:
    if not x_notes_key or not secrets.compare_digest(x_notes_key, NOTES_API_KEY):
        raise HTTPException(status_code=401, detail="unauthorized")

    projects_out = storage.list_tree(prefix="notes/")
    return {
        "status": "ok",
        "projects": projects_out,
    }
