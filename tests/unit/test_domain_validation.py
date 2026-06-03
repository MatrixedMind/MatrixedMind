import pytest

from app.domain.validation import (
    MAX_MARKDOWN_LENGTH,
    MAX_SLUG_LENGTH,
    MAX_TITLE_LENGTH,
    validate_markdown,
    validate_path,
    validate_slug,
    validate_title,
)


@pytest.mark.parametrize("slug", ["home", "hello-world", "abc123", "a-1-b"])
def test_validate_slug_accepts_canonical_slugs(slug: str) -> None:
    assert validate_slug(slug) == slug


def test_validate_slug_accepts_numeric_slugs() -> None:
    assert validate_slug("123") == "123"


@pytest.mark.parametrize(
    "slug",
    [
        "",
        "Hello",
        "hello_world",
        "-hello",
        "hello-",
        "hello--world",
        "a" * (MAX_SLUG_LENGTH + 1),
    ],
)
def test_validate_slug_rejects_invalid_slugs(slug: str) -> None:
    with pytest.raises(ValueError):
        validate_slug(slug)


@pytest.mark.parametrize("path", ["/", "/home", "/spaces/personal-notes", "/a-1/b-2"])
def test_validate_path_accepts_absolute_slug_paths(path: str) -> None:
    assert validate_path(path) == path


@pytest.mark.parametrize(
    "path",
    [
        "",
        "home",
        "/Home",
        "/home/",
        "/home//child",
        "/../parent-folder",
        "/./current-folder",
    ],
)
def test_validate_path_rejects_invalid_paths(path: str) -> None:
    with pytest.raises(ValueError):
        validate_path(path)


def test_validate_title_strips_outer_whitespace() -> None:
    assert validate_title("  Hello World  ") == "Hello World"


@pytest.mark.parametrize("title", ["", "   ", "a" * (MAX_TITLE_LENGTH + 1)])
def test_validate_title_rejects_invalid_titles(title: str) -> None:
    with pytest.raises(ValueError):
        validate_title(title)


def test_validate_markdown_accepts_non_empty_markdown() -> None:
    assert validate_markdown("# Hello\nBody") == "# Hello\nBody"


@pytest.mark.parametrize("body", ["", "   ", "hello\x00world"])
def test_validate_markdown_rejects_invalid_markdown(body: str) -> None:
    with pytest.raises(ValueError):
        validate_markdown(body)


def test_validate_markdown_rejects_over_limit_body() -> None:
    with pytest.raises(ValueError):
        validate_markdown("a" * (MAX_MARKDOWN_LENGTH + 1))
