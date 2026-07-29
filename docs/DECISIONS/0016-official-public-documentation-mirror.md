# 0016: Make the Official Public Documentation Mirror Opt-In

## Status

Accepted

## Context

MatrixedMind plans to mirror approved project documentation as a public site. That publishing path
must remain distinct from the default private personal-knowledge workflow, especially for
self-hosted installations.

Repository documentation also contains relative links. A mirror needs deterministic link behavior
so published records do not depend on the publisher's working directory or repository-view URL.

## Decision

The official public documentation mirror is an opt-in feature. It uses a deliberately configured
official documentation source and is separate from default self-hosted configuration.

A default self-hosted MatrixedMind instance has no official public documentation source configured
and must never publish MatrixedMind's documentation automatically. Enabling general public records
or deploying MatrixedMind does not implicitly enable the official mirror.

Publishing will begin as a manual, reviewed workflow. Automatic publishing on source-repository
changes is deferred. The exact official source and review policy must be confirmed before the first
publication.

Supported repository-relative links should ultimately translate deterministically to the
corresponding public documentation records. The publishing workflow must detect supported links
whose targets cannot be mirrored rather than silently producing ambiguous destinations.

This ADR defines publishing boundaries and future link behavior. It does not claim that the mirror,
public routes, publishing workflow, or link translation is implemented.

## Consequences

### Positive

- Prevents self-hosted instances from unexpectedly publishing MatrixedMind project content.
- Makes the official source and publication action deliberate and reviewable.
- Preserves a manual safety checkpoint before automation is considered.
- Provides a stable direction for repository-relative links in the public site.

### Negative

- Publication initially requires a manual review and release step.
- Source configuration, unpublishing, and broken-link handling need explicit implementation.
- Automatic synchronization remains unavailable until a later decision and implementation.

## Verification expectations

- A default self-hosted configuration has no official documentation source and publishes no
  MatrixedMind documentation.
- Only the deliberately configured source can feed the official mirror.
- The manual workflow requires review before publishing or unpublishing records.
- Tests prove private records and protected routes remain inaccessible through the public
  documentation surface.
- Supported repository-relative links resolve deterministically, and missing mirror targets are
  reported.
