import re

SLUG_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
MAX_SLUG_LENGTH = 80
MAX_PATH_LENGTH = 512
MAX_TITLE_LENGTH = 200
# Markdown bodies are bounded to keep local request validation and database writes predictable
# while still allowing large long-form notes during the pre-MVP milestones.
MAX_MARKDOWN_LENGTH = 1_000_000


def validate_slug(value: str) -> str:
    if not isinstance(value, str):
        raise TypeError("slug must be a string")
    if not value:
        raise ValueError("slug must not be empty")
    if len(value) > MAX_SLUG_LENGTH:
        raise ValueError(f"slug must be {MAX_SLUG_LENGTH} characters or fewer")
    if not SLUG_PATTERN.fullmatch(value):
        raise ValueError("slug must use lowercase letters, numbers, and single hyphens")
    return value


def validate_path(value: str) -> str:
    if not isinstance(value, str):
        raise TypeError("path must be a string")
    if not value:
        raise ValueError("path must not be empty")
    if len(value) > MAX_PATH_LENGTH:
        raise ValueError(f"path must be {MAX_PATH_LENGTH} characters or fewer")
    if value == "/":
        return value
    if not value.startswith("/"):
        raise ValueError("path must start with '/'")
    if value.endswith("/"):
        raise ValueError("path must not end with '/'")

    for segment in value.removeprefix("/").split("/"):
        validate_slug(segment)
    return value


def validate_title(value: str) -> str:
    if not isinstance(value, str):
        raise TypeError("title must be a string")
    title = value.strip()
    if not title:
        raise ValueError("title must not be empty")
    if len(title) > MAX_TITLE_LENGTH:
        raise ValueError(f"title must be {MAX_TITLE_LENGTH} characters or fewer")
    return title


def validate_markdown(value: str) -> str:
    if not isinstance(value, str):
        raise TypeError("Markdown body must be a string")
    if "\x00" in value:
        raise ValueError("Markdown body must not contain null bytes")
    if not value.strip():
        raise ValueError("Markdown body must not be empty")
    if len(value) > MAX_MARKDOWN_LENGTH:
        raise ValueError(f"Markdown body must be {MAX_MARKDOWN_LENGTH} characters or fewer")
    return value
