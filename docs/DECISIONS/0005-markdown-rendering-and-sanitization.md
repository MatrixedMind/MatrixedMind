# 0005: Render Markdown with markdown-it-py and nh3

## Status

Accepted

## Context

MatrixedMind stores Markdown-first records and needs to render them in server-rendered pages without allowing stored content to become executable browser content.

The current project dependency set already includes `markdown-it-py` and `nh3`, so the implementation direction has effectively been chosen. Leaving the roadmap item open would invite agents to re-evaluate the rendering stack after code already depends on it.

## Decision

Use `markdown-it-py` as the Markdown renderer and `nh3` as the HTML sanitizer.

Render Markdown through a small application-owned rendering boundary instead of calling the renderer directly from route handlers or templates. Sanitize the rendered HTML before it is marked safe for templates.

Use a restrictive sanitizer policy by default:

- Allow normal document structure such as headings, paragraphs, lists, code blocks, blockquotes, tables, emphasis, and links.
- Reject scriptable HTML, inline event handlers, embedded scripts, unsafe URL schemes, and raw HTML that is not explicitly allowlisted.
- Allow only safe URL schemes such as `http`, `https`, and relative links unless a future ADR expands the policy.
- Add tests for malicious Markdown and raw HTML fixtures before expanding the allowlist.

## Consequences

### Positive

- Keeps Markdown rendering simple and Python-native.
- Avoids adding a frontend rendering dependency before the UI needs one.
- Gives the app a clear security boundary for rendered user content.
- Makes sanitizer behavior testable and reusable across web pages, exports, previews, and future API responses.

### Negative

- Markdown extension behavior is constrained by `markdown-it-py` and available plugins.
- Some HTML or Markdown features may be blocked until explicitly reviewed and tested.
- The sanitizer allowlist becomes a compatibility surface that must be handled carefully when content already exists.

## Verification expectations

- Tests prove safe Markdown renders as expected.
- Tests prove script tags, inline event handlers, and `javascript:` links are removed or neutralized.
- Web route tests verify rendered record pages use sanitized HTML.
