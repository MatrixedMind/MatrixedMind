# 0018: Portable Identity Adapters and MatrixedMind-Owned Sessions

## Status

Accepted

## Context

MatrixedMind must be useful as self-hosted software without requiring a cloud identity provider.
A Mind is one owner's personal body of knowledge in an Instance. The existing dev/test identity
boundary and Custom GPT Action bearer-token path do not provide a complete browser-authentication
model for a Mind owner. ADR 0008 correctly required fail-closed
production behavior, but its prohibition on MatrixedMind password storage conflicts with the
approved portable local-first direction.

## Decision

MatrixedMind provides built-in local password authentication as the default owner-authentication
path. Passwords are stored only as Argon2id hashes with the necessary per-credential metadata;
plaintext passwords and shared-secret browser identity are prohibited.

MatrixedMind owns browser sessions. It creates, validates, rotates, revokes, and expires sessions
and maps authenticated identities to MatrixedMind users. Sessions have configurable inactivity and
absolute expiration and rotation intervals. Initial defaults are 30 days of inactivity, 90 days
absolute, and rotation after eight hours of use. Rotation renews an active session credential; it
does not force another interactive login.

Initial owner bootstrap and recovery are explicit, secure, local-owner-controlled flows. They must
not manufacture a default password, expose a reusable setup path after initialization, or require a
remote provider. Browser writes require CSRF protection, and hosted deployments use secure cookie
settings.

Firebase and generic OIDC are optional identity adapters. They may prove an external identity, but
they do not own MatrixedMind authorization, its user model, or browser-session policy. Hosted/GCP
integration is likewise optional. MCP is an optional Connection integration, not an identity
provider.

The current Custom GPT Action and scoped bearer-token API remain implemented legacy/provisional
support. They may be retired only after a replacement has equivalent or stronger scope, revocation,
attribution, audit, migration, and rollback evidence. No retirement is decided by this ADR.

The bearer-token primitive becomes a provider-neutral personal access token (PAT) for scripts and
legacy clients. PATs remain hashed at rest and require an explicit actor, owner, operation scope,
Space scope, and revocation state. A PAT is a credential, not a Connection or access grant; those
separate concepts arrive in a later milestone. The existing Action routes remain compatibility
surfaces, but the physical PAT collection and index use `personal_access_tokens` without a legacy
alias or automatic migration. Because MatrixedMind has no active users, existing pre-use PATs must
be reissued after a clean database reset or a separately approved migration.

Before real owner identities are enabled, Page persistence must qualify reads, lists, updates, and
uniqueness by owner. Record mutation, revision creation, and required audit recording must also
have a defined atomic failure contract before PATs or Connections are considered durable automation.

This ADR supersedes ADR 0008 where ADR 0008 prohibits MatrixedMind password storage or requires a
managed provider for production browser identity. Its dev/test separation and fail-closed
requirements continue to apply.

## Consequences

### Positive

- A local Instance can be securely owned without Firebase, OIDC, or GCP.
- Identity providers remain replaceable adapters rather than product dependencies.
- Browser-session policy and authorization remain portable and MatrixedMind-owned.

### Negative

- MatrixedMind must implement and test credential, recovery, session, and CSRF security carefully.
- Operators must make an explicit configuration choice for session lifetimes.
- Provider adapters require mapping and logout behavior that stays consistent with local auth.

## Verification expectations

- Test Argon2id hashing and verification; never persist or log a plaintext credential.
- Test secure bootstrap, recovery, sign-in, sign-out, password change, and rejected insecure or
  repeated setup attempts.
- Test rotation, inactivity expiry, absolute expiry, revocation, CSRF denial, cookie behavior, and
  fail-closed protected routes.
- Test owner-qualified Page isolation and PAT rotation, uniqueness, collision, and revocation
  behavior through shared repository contracts.
- Test that a clean local Instance operates without optional provider packages or configuration.
- Test provider adapters as optional integrations and prove they retain MatrixedMind authorization
  and session controls.
