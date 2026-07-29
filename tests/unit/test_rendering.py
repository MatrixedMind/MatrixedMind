import pytest

from app.rendering import is_safe_external_image_url, render_safe_markdown


def test_approved_https_markdown_image_renders_required_attributes_only() -> None:
    rendered = render_safe_markdown(
        '![Diagram](https://images.example.com/diagram.png "Architecture")'
    )

    assert '<img src="https://images.example.com/diagram.png"' in rendered
    assert 'alt="Diagram"' in rendered
    assert 'title="Architecture"' in rendered
    assert "style=" not in rendered
    assert "onerror=" not in rendered


@pytest.mark.parametrize(
    "url",
    [
        "http://images.example.com/image.png",
        "//images.example.com/image.png",
        "data:image/png;base64,abc",
        "javascript:alert(1)",
        "https://user@example.com/image.png",
        "https://images.example.com:8443/image.png",
        "https://[invalid/image.png",
        "https://localhost/image.png",
        "https://127.0.0.1/image.png",
        "https://-images.example.com/image.png",
        "https://images.example-.com/image.png",
    ],
)
def test_unsafe_external_image_url_is_rejected(url: str) -> None:
    assert not is_safe_external_image_url(url)


def test_blocked_image_is_neutralized_without_losing_alt_text() -> None:
    rendered = render_safe_markdown("![Blocked](http://images.example.com/image.png)")

    assert "<img" not in rendered
    assert "Blocked" in rendered


def test_exact_image_source_allowlist_rejects_other_and_deceptive_hosts() -> None:
    allowlist = "images.example.com"

    assert is_safe_external_image_url(
        "https://images.example.com/image.png", ("images.example.com",)
    )
    assert not is_safe_external_image_url(
        "https://cdn.images.example.com/image.png", ("images.example.com",)
    )
    assert not is_safe_external_image_url(
        "https://images.example.com.attacker.test/image.png", ("images.example.com",)
    )
    assert "<img" not in render_safe_markdown(
        "![Blocked](https://attacker.test/image.png)", allowlist
    )


def test_wildcard_image_source_allowlist_requires_a_real_subdomain() -> None:
    allowed_sources = ("*.example.com",)

    assert is_safe_external_image_url("https://images.example.com/image.png", allowed_sources)
    assert not is_safe_external_image_url("https://example.com/image.png", allowed_sources)
    assert not is_safe_external_image_url(
        "https://example.com.attacker.test/image.png", allowed_sources
    )


def test_unicode_image_source_allowlist_is_normalized_to_idna() -> None:
    rendered = render_safe_markdown(
        "![Image](https://images.xn--bcher-kva.example/image.png)",
        "images.bücher.example",
    )

    assert '<img src="https://images.xn--bcher-kva.example/image.png"' in rendered


def test_raw_html_cannot_bypass_image_policy() -> None:
    rendered = render_safe_markdown(
        '<img src="https://images.example.com/image.png" onerror="alert(1)" style="display:none">'
    )

    assert rendered == '<img src="https://images.example.com/image.png">'
    assert "onerror=" not in rendered
    assert "style=" not in rendered


def test_raw_html_with_unsafe_image_url_is_neutralized() -> None:
    rendered = render_safe_markdown('<img src="http://images.example.com/image.png">')

    assert rendered == "<img>"


def test_safe_non_image_links_keep_existing_supported_schemes() -> None:
    rendered = render_safe_markdown("[Example](http://example.com)")

    assert 'href="http://example.com"' in rendered
