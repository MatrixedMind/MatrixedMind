from collections.abc import Iterable
from ipaddress import ip_address
from urllib.parse import urlsplit

import nh3
from markdown_it import MarkdownIt
from markdown_it.token import Token

_MARKDOWN = MarkdownIt()

_ALLOWED_HTML_TAGS: set[str] = {
    "a",
    "blockquote",
    "br",
    "code",
    "em",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "hr",
    "img",
    "li",
    "ol",
    "p",
    "pre",
    "strong",
    "ul",
}

_ALLOWED_HTML_ATTRIBUTES: dict[str, set[str]] = {
    "a": {"href", "title"},
    "img": {"alt", "src", "title"},
}

_ALLOWED_HTML_SCHEMES: set[str] = {"http", "https", "mailto"}


def _normalized_hostname(hostname: str) -> str | None:
    try:
        normalized = hostname.encode("idna").decode("ascii").lower().rstrip(".")
    except UnicodeError:
        return None
    try:
        ip_address(normalized)
    except ValueError:
        pass
    else:
        return None
    labels = normalized.split(".")
    if (
        len(normalized) > 253
        or len(labels) < 2
        or any(
            not label
            or len(label) > 63
            or label.startswith("-")
            or label.endswith("-")
            or not label.replace("-", "a").isalnum()
            for label in labels
        )
    ):
        return None
    return normalized


def normalize_image_source_allowlist(value: str) -> tuple[str, ...]:
    """Return normalized exact or wildcard host patterns from a comma-separated setting."""
    sources: list[str] = []
    for untrusted_source in value.split(","):
        source = untrusted_source.strip().lower().rstrip(".")
        if not source:
            continue
        wildcard_prefix = "*." if source.startswith("*.") else ""
        hostname = _normalized_hostname(source.removeprefix("*."))
        if not hostname or ":" in hostname or "/" in hostname or "@" in hostname:
            raise ValueError(
                "MARKDOWN_IMAGE_SOURCE_ALLOWLIST entries must be exact hostnames "
                "or *.domain wildcards"
            )
        sources.append(f"{wildcard_prefix}{hostname}")
    return tuple(dict.fromkeys(sources))


def _source_is_allowed(hostname: str, allowed_sources: Iterable[str]) -> bool:
    configured_sources = tuple(allowed_sources)
    if not configured_sources:
        return True
    return any(
        hostname == source
        if not source.startswith("*.")
        else hostname.endswith(f".{source[2:]}") and hostname != source[2:]
        for source in configured_sources
    )


def is_safe_external_image_url(url: str, allowed_sources: Iterable[str] = ()) -> bool:
    """Accept browser-rendered images only from safe HTTPS sources."""
    try:
        parsed = urlsplit(url)
        port = parsed.port
    except ValueError:
        return False

    if (
        parsed.scheme.lower() != "https"
        or parsed.username is not None
        or parsed.password is not None
        or parsed.hostname is None
        or port not in (None, 443)
    ):
        return False

    hostname = _normalized_hostname(parsed.hostname)
    return hostname is not None and _source_is_allowed(hostname, allowed_sources)


def _apply_image_policy(tokens: list[Token], allowed_sources: tuple[str, ...]) -> None:
    for token in tokens:
        if token.children:
            _apply_image_policy(token.children, allowed_sources)
        if token.type != "image":
            continue
        source = token.attrGet("src")
        if isinstance(source, str) and is_safe_external_image_url(source, allowed_sources):
            continue

        token.type = "text"
        token.tag = ""
        token.attrs = {}
        token.children = None


def render_safe_markdown(markdown_text: str, image_source_allowlist: str = "") -> str:
    allowed_sources = normalize_image_source_allowlist(image_source_allowlist)
    tokens = _MARKDOWN.parse(markdown_text)
    _apply_image_policy(tokens, allowed_sources)
    rendered_html = _MARKDOWN.renderer.render(tokens, _MARKDOWN.options, {})

    def attribute_filter(tag: str, attribute: str, value: str) -> str | None:
        if tag == "img" and attribute == "src":
            return value if is_safe_external_image_url(value, allowed_sources) else None
        return value

    return nh3.clean(
        rendered_html,
        tags=_ALLOWED_HTML_TAGS,
        clean_content_tags={"script", "style"},
        attributes=_ALLOWED_HTML_ATTRIBUTES,
        attribute_filter=attribute_filter,
        url_schemes=_ALLOWED_HTML_SCHEMES,
    )
