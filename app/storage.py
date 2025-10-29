import os
from typing import Any, Dict, List, Sequence, Tuple
from urllib.parse import quote
from google.cloud import storage
from fastapi import HTTPException

BUCKET_NAME = os.environ.get("NOTES_BUCKET")
if not BUCKET_NAME:
    raise RuntimeError("NOTES_BUCKET env var missing")

client = storage.Client()
bucket = client.bucket(BUCKET_NAME)

LEGACY_SAFE_CHARS = "-_.()[]{}!@#$%^&+=,;'%'"  # includes % to avoid re-encoding legacy names


def sanitize(segment: str) -> str:
    r"""
    Sanitize a segment for use in GCS object paths.
    
    Replaces whitespace with underscores and removes/replaces characters
    that could be problematic in GCS paths, including:
    - Path separators (/, \)
    - Control characters
    - Special characters that could cause issues

    This prevents path traversal attacks and unexpected storage behavior.
    Additional enforcement (such as bucket-level object restrictions) should
    be configured separately; this helper focuses on building safe object
    paths while preserving compatibility with existing blobs.
    """
    # First, strip leading/trailing whitespace
    segment = segment.strip()
    
    # Replace internal whitespace with underscores
    segment = "_".join(segment.split())
    
    # Remove control characters (ASCII 0-31 and 127)
    segment = "".join(char for char in segment if ord(char) >= 32 and ord(char) != 127)
    
    # Replace path separators with underscores to prevent path traversal while
    # preserving characters that were historically valid in segment names.
    segment = segment.replace("/", "_").replace("\\", "_")

    # Percent-encode any remaining characters that fall outside our legacy-safe
    # set so that GCS receives a deterministic, traversal-safe object name
    # without breaking existing blobs that relied on those characters.
    segment = quote(segment, safe=LEGACY_SAFE_CHARS)
    
    # Remove leading/trailing underscores that may result from sanitization
    segment = segment.strip("_")
    
    # If the segment is empty after sanitization, return a safe default
    if not segment:
        segment = "unnamed"
    
    return segment

def _section_segments(section: str | Sequence[str] | None) -> List[Tuple[str, str]]:
    if section is None:
        return []

    if isinstance(section, str):
        raw_parts = [part.strip() for part in section.split("/") if part.strip()]
    else:
        raw_parts = [str(part).strip() for part in section if str(part).strip()]
    return [(raw, sanitize(raw)) for raw in raw_parts]


def note_path(project: str, section: str, title: str) -> str:
    """Build the canonical storage path for a note, allowing nested sections."""
    sections = [san for _, san in _section_segments(section)]
    parts = [sanitize(project), *sections, f"{sanitize(title)}.md"]
    return "notes/" + "/".join(parts)

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
    sections = [san for _, san in _section_segments(section)]
    parts = [sanitize(project), *sections, "_index.md"]
    return "notes/" + "/".join(parts)

def ensure_index_files(project: str, section: str) -> None:
    section_pairs = _section_segments(section)
    if not section_pairs:
        return

    top_section_label = section_pairs[0][0]
    project_index_blob = bucket.blob(_index_path(project))
    if not project_index_blob.exists():
        project_index_blob.upload_from_string(
            f"# {project}\n\nSections:\n- [[{top_section_label}]]\n"
        )
    else:
        current = project_index_blob.download_as_text()
        if "Sections:\n" not in current:
            current = current.rstrip() + "\n\nSections:\n"
        link_line = f"- [[{top_section_label}]]"
        if link_line not in current:
            current = current.rstrip() + "\n" + link_line + "\n"
            project_index_blob.upload_from_string(current)

    for idx, (raw_name, _) in enumerate(section_pairs, start=1):
        current_section = "/".join(pair[0] for pair in section_pairs[:idx])
        section_blob = bucket.blob(_index_path(project, current_section))
        default_content = (
            f"# {raw_name}\n\nSections:\n\nNotes in this section:\n"
        )
        if not section_blob.exists():
            section_blob.upload_from_string(default_content)
        else:
            existing = section_blob.download_as_text()
            updated = existing
            if "Sections:\n" not in existing:
                updated = updated.rstrip() + "\n\nSections:\n"
            if "Notes in this section:\n" not in existing:
                updated = updated.rstrip() + "\n\nNotes in this section:\n"
            if updated != existing:
                section_blob.upload_from_string(updated)

        if idx == 1:
            continue

        parent_section = "/".join(pair[0] for pair in section_pairs[: idx - 1])
        parent_blob = bucket.blob(_index_path(project, parent_section))
        if not parent_blob.exists():
            # Create the parent blob with default content if it doesn't exist
            parent_raw_name = section_pairs[idx - 2][0]
            parent_default_content = f"# {parent_raw_name}\n\nSections:\n\nNotes in this section:\n"
            parent_blob.upload_from_string(parent_default_content)
            parent_content = parent_default_content
        else:
            parent_content = parent_blob.download_as_text()
        if "Sections:\n" not in parent_content:
            parent_content = parent_content.rstrip() + "\n\nSections:\n"
        link_line = f"- [[{raw_name}]]"
        if link_line not in parent_content:
            parent_content = parent_content.rstrip() + "\n" + link_line + "\n"
            parent_blob.upload_from_string(parent_content)

def update_section_index(project: str, section: str, title: str) -> None:
    blob = bucket.blob(_index_path(project, section))
    if not blob.exists():
        blob.upload_from_string(f"# {section}\n\nNotes in this section:\n- [[{title}]]\n")
        return

    current = blob.download_as_text()
    link_line = f"- [[{title}]]"
    updated = current
    if "Notes in this section:\n" not in current:
        updated = updated.rstrip() + "\n\nNotes in this section:\n"
    if link_line not in updated:
        updated = updated.strip() + "\n" + link_line + "\n"
    if updated != current:
        blob.upload_from_string(updated)

def list_tree(prefix: str = "notes/") -> List[Dict[str, Any]]:
    # Walk the bucket under the given prefix and return the same nested structure
    blobs = bucket.list_blobs(prefix=prefix)
    tree = {}

    for b in blobs:
        if b.name.endswith("/"):
            continue
        parts = b.name.split("/")
        if len(parts) < 4:
            continue
        _, project, *section_parts, filename = parts
        if filename == "_index.md":
            continue
        title = filename[:-3] if filename.endswith(".md") else filename

        proj = tree.setdefault(project, {})
        section_key = "/".join(section_parts)
        sec = proj.setdefault(section_key, [])
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
