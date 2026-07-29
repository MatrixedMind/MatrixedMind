# 0017: Allow Safe External HTTPS Markdown Images

## Status

Accepted

## Context

MatrixedMind currently sanitizes rendered Markdown through the boundary defined by ADR 0013.
Milestone 11 needs externally hosted images without turning stored Markdown into an executable or
unbounded HTML surface.

Some deployments may want to restrict image sources to controlled hosts, including a configured
object-storage bucket. Image upload and attachment storage are separate concerns and are not needed
to safely render already-hosted images.

## Decision

Milestone 11 will support images that resolve to safe external HTTPS URLs. Deployments may configure
an image-source allowlist; when configured, an image must also match an allowed source, including a
specifically configured bucket host when applicable.

Sanitization will preserve only attributes necessary to render an approved image. Unsafe URL
schemes, raw event handlers, and inline styles are rejected. Raw HTML must not bypass the same image
policy applied to Markdown image syntax.

Image uploads, object-storage provisioning, and storage-backed attachments are out of scope for
Milestone 11. A later attachment design must remain portable beyond GCP rather than making the
domain model depend on a GCP-specific storage service.

This ADR extends the policy direction in ADR 0013. It does not claim external-image rendering,
allowlist configuration, uploads, or attachment storage are currently implemented.

## Consequences

### Positive

- Enables useful hosted images while preserving the existing sanitization boundary.
- Lets security-sensitive deployments constrain image fetches to approved hosts.
- Avoids coupling the Milestone 11 renderer to an upload or cloud-storage implementation.
- Preserves a portable path for later storage-backed attachments.

### Negative

- External images disclose a viewer request to the approved image host and can become unavailable
  independently of MatrixedMind.
- Source allowlists add configuration and testing complexity.
- Content that depends on unsupported attributes, schemes, or inline styling will not render as
  authored.

## Verification expectations

- Approved external HTTPS images render with only the required attributes preserved.
- Non-HTTPS and otherwise unsafe image URLs are removed or neutralized.
- Event-handler attributes and inline styles are removed from image markup.
- Raw HTML cannot bypass the Markdown image policy.
- When an image-source allowlist is configured, approved hosts or bucket sources render and other
  hosts do not.
- Tests confirm that no upload or object-storage behavior is implied by external-image rendering.
