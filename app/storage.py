import os
import time
import re
from typing import Any, Dict, List
from google.cloud import storage
from google.api_core import exceptions

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
    """
    Generate path for a note with support for nested subsections.
    
    Args:
        project: Project name
        section: Section path (can include subsections separated by '/')
        title: Note title
    
    Returns:
        Path like: notes/<project>/<section>/<subsection>/<title>.md
    """
    # Split section by '/' to handle nested subsections
    section_parts = [sanitize(part) for part in section.split("/") if part]
    section_path = "/".join(section_parts)
    return f"notes/{sanitize(project)}/{section_path}/{sanitize(title)}.md"

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
    """
    Generate index path for a project or section.
    
    Args:
        project: Project name
        section: Section path (can include subsections separated by '/')
    
    Returns:
        Path like: notes/<project>/_index.md or notes/<project>/<section>/_index.md
    """
    if section is None:
        return f"notes/{sanitize(project)}/_index.md"
    else:
        # Split section by '/' to handle nested subsections
        section_parts = [sanitize(part) for part in section.split("/") if part]
        section_path = "/".join(section_parts)
        return f"notes/{sanitize(project)}/{section_path}/_index.md"

def _retry_on_conflict(func, max_retries: int = 5):
    """Retry a function that may encounter precondition failures due to concurrent updates."""
    for attempt in range(max_retries):
        try:
            return func()
        except exceptions.NotFound:
            # NotFound indicates a permanent error (blob doesn't exist), not a transient conflict
            # Re-raise immediately without retrying
            raise
        except exceptions.PreconditionFailed:
            if attempt == max_retries - 1:
                raise
            # Exponential backoff: 0.1s, 0.2s, 0.4s, 0.8s
            time.sleep(0.1 * (2 ** attempt))
    
    # This line should never be reached due to the return or raise in the loop
    # but added for clarity and to satisfy linters
    return None

def ensure_index_files(project: str, section: str) -> None:
    """
    Ensure project and section index files exist with atomic operations to prevent race conditions.
    
    This function handles nested subsections by:
    1. Creating/updating the project-level index with the top-level section
    2. Creating index files for each level of nested subsections
    """
    
    # Split section into parts for nested subsections
    section_parts = [part for part in section.split("/") if part]
    
    if not section_parts:
        return
    
    # Get the top-level section name for the project index
    top_level_section = section_parts[0]
    
    # Update project-level index with the top-level section only
    def _update_project_index():
        project_path = _index_path(project)
        blob = bucket.blob(project_path)
        
        # Try to create first - this will fail if blob already exists
        try:
            blob.upload_from_string(
                f"# {project}\n\nSections:\n- [[{top_level_section}]]\n",
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
            raise exceptions.PreconditionFailed("Failed to retrieve blob generation for atomic update. The blob may have been deleted.")

        current = blob.download_as_text(if_generation_match=generation)
        link_line = f"- [[{top_level_section}]]"

        if link_line in current:
            # Already present, nothing to do
            return
        
        # Update content and upload only if generation hasn't changed
        new_content = current.strip() + "\n" + link_line + "\n"
        blob.upload_from_string(new_content, if_generation_match=generation)
    
    _retry_on_conflict(_update_project_index)
    
    # Create index files for each level of the nested section hierarchy
    for i in range(len(section_parts)):
        # Build the partial section path (e.g., "section", "section/subsection1", etc.)
        partial_section = "/".join(section_parts[:i+1])
        section_path = _index_path(project, partial_section)
        blob = bucket.blob(section_path)
        
        # Determine the display name for this level
        display_name = section_parts[i]
        
        # Try to create - if it fails, blob already exists (which is fine)
        try:
            if i < len(section_parts) - 1:
                # This is an intermediate level - it might have subsections
                blob.upload_from_string(
                    f"# {display_name}\n\nSubsections and notes:\n",
                    if_generation_match=0
                )
            else:
                # This is the final level - it contains notes
                blob.upload_from_string(
                    f"# {display_name}\n\nNotes in this section:\n",
                    if_generation_match=0
                )
        except exceptions.PreconditionFailed:
            # Blob already exists from another process, no action needed
            pass
        
        # If there's a next level, update the current level's index to link to it
        if i < len(section_parts) - 1:
            next_subsection = section_parts[i+1]
            
            def _update_subsection_index():
                blob = bucket.blob(section_path)
                
                # Blob should exist (we just created it or it existed), reload to get generation
                blob.reload()
                generation = blob.generation
                if generation is None:
                    # If blob doesn't exist, we can skip updating it
                    return
                
                try:
                    current = blob.download_as_text(if_generation_match=generation)
                except exceptions.NotFound:
                    # Blob was deleted between reload and download, skip
                    return
                
                link_line = f"- [[{next_subsection}]]"
                
                if link_line in current:
                    # Already present, nothing to do
                    return
                
                # Update content and upload only if generation hasn't changed
                new_content = current.strip() + "\n" + link_line + "\n"
                try:
                    blob.upload_from_string(new_content, if_generation_match=generation)
                except exceptions.PreconditionFailed:
                    # Generation changed, will retry
                    raise
            
            _retry_on_conflict(_update_subsection_index)

def update_section_index(project: str, section: str, title: str) -> None:
    """Update section index with atomic operations to prevent race conditions."""
    path = _index_path(project, section)
    
    # Get the last part of the section for display name
    section_parts = [part for part in section.split("/") if part]
    display_name = section_parts[-1] if section_parts else section
    
    def _update():
        blob = bucket.blob(path)
        
        # Try to create first - this will fail if blob already exists
        try:
            blob.upload_from_string(
                f"# {display_name}\n\nNotes in this section:\n- [[{title}]]\n",
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
            raise exceptions.PreconditionFailed("Failed to retrieve blob generation for atomic update. The blob may have been deleted.")

        current = blob.download_as_text(if_generation_match=generation)
        link_line = f"- [[{title}]]"

        if link_line in current.splitlines():
            # Already present, nothing to do
            return
        
        # Update content and upload only if generation hasn't changed
        new_content = current.strip() + "\n" + link_line + "\n"
        blob.upload_from_string(new_content, if_generation_match=generation)
    
    _retry_on_conflict(_update)

def list_tree(prefix: str = "notes/") -> List[Dict[str, Any]]:
    """
    Walk the bucket under the given prefix and return a nested structure.
    
    Now supports arbitrary depth of subsections. The structure returned is:
    - projects: list of projects, each with:
      - name: project name
      - sections: list of sections, each with:
        - name: section path (e.g., "section/subsection1/subsection2")
        - notes: list of note titles
    """
    blobs = bucket.list_blobs(prefix=prefix)
    tree = {}

    for b in blobs:
        if b.name.endswith("/"):
            continue
        parts = b.name.split("/")
        # Must have at least: notes/project/section/filename (4 parts minimum)
        if len(parts) < 4:
            continue
        
        # First part is "notes", second is project, last is filename, everything in between is the section path
        project = parts[1]
        filename = parts[-1]
        section_parts = parts[2:-1]  # Everything between project and filename
        
        if filename == "_index.md":
            continue
        
        title = filename[:-3] if filename.endswith(".md") else filename
        
        # Join section parts back together to form the full section path
        section = "/".join(section_parts)

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
