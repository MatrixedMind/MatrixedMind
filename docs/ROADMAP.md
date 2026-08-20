# MatrixedMind Roadmap

## Product language

- **MatrixedMind software** is the portable, self-hostable product.
- An **Instance** is one deployment of the MatrixedMind software.
- A **Mind** is one owner's personal body of knowledge in an Instance.
- A **Mind owner** owns and controls that Mind.
- A **Space** is a collection within a Mind.
- A **Connection** is an external actor or integration granted constrained access.
- A **Page** is user content. **Record** remains the internal implementation term.

## Direction

MatrixedMind is one modular monorepo and one deployable application by default. It must run as a
provider-free OCI container with local ownership as the baseline. Firebase, generic OIDC, MCP, and
hosted/GCP support are optional adapters and dependency groups, not requirements for a local
Instance. Do not use git submodules. Extract a component only when it has an independent lifecycle
and the operational benefit exceeds the added boundary.

Durable user guidance, contracts, and accepted decisions belong in this repository. Roadmap
milestones describe product direction, release scope, and sequencing. GitHub Milestones group issues
into releasable capabilities. Actionable implementation work belongs in bounded, independently
reviewable GitHub Issues that collectively satisfy a milestone. Accepted architectural decisions
belong in ADRs under `docs/DECISIONS/`, while unresolved decisions and actionable implementation
tasks belong in GitHub Issues.

## Completed foundation: Milestones 0–12

Milestones 0–12 are complete and verified as their delivery sequence:

| Milestone | Delivered capability |
|---|---|
| 0–4 | FastAPI modular-monolith foundation, record API, validation, repository contracts, and MongoDB adapter. |
| 5–6 | Server-rendered browser shell, safe Markdown, private/indexing defaults, initial owner boundary, authorization policy, and narrow PAT boundary. |
| 7–9 | Firestore MongoDB compatibility work, CI, Terraform layout, Cloud Run deployment baseline, and passwordless GCP runtime access. |
| 10–12 | Narrow Custom GPT Action contract, hosted activation topology, operational hardening, secret-rotation exercise, restore validation, and production-index readiness. |

The current Custom GPT Action and scoped-token path is implemented **legacy/provisional** support.
It remains in service until a safe replacement exists; its retirement is not yet planned or
implemented.

## Milestone 13: Portable owner authentication and UI foundation

**Status:** Complete locally. Hosted activation is gated in Milestone 14.

The local-first owner experience runs without a cloud identity provider. The current record model
remains the internal compatibility boundary behind the server-rendered Page UI.

### Resolved human decisions

- Local password authentication is built in; credentials use Argon2id.
- MatrixedMind owns browser sessions, session rotation, and expiration enforcement.
- Session inactivity, absolute expiration, and rotation intervals are configurable. Initial
  defaults are 30 days of inactivity, 90 days absolute, and rotation after eight hours of use.
  Rotation does not require the owner to sign in again.
- First-use bootstrap and recovery are secure, explicit, and local-owner controlled; they must not
  create a default credential or a remote recovery dependency.
- Provider identity is optional: Firebase and generic OIDC are adapters, not the core path.
- The product terms in this roadmap are the canonical user-facing vocabulary.

### Implementation criteria

- Make Page repository reads, lists, updates, and uniqueness owner-qualified before introducing
  real owner identities. Prove that two owners can use the same Space and Page slug without
  collision or existence disclosure. Hosted index migration is additive-first and remains a
  separately approved cloud operation.
- Implement local owner credential setup, sign-in, sign-out, password change, and secure recovery
  behind an application-owned auth boundary.
- Store only Argon2id password hashes and necessary credential metadata; never store plaintext
  credentials or use a shared-secret browser identity shortcut.
- Implement MatrixedMind-owned secure browser sessions with rotation, configurable inactivity and
  absolute expiry, CSRF protection for browser writes, and secure hosted-cookie behavior.
- Establish a small, accessible server-rendered UI foundation using Page, Space, and Mind
  language while retaining internal Record compatibility.
- Preserve fail-closed behavior for protected browser and internal API routes.
- Define adapter seams and optional dependency groups for Firebase and generic OIDC without making
  either required to run locally.
- Generalize the existing scoped bearer-token internals into provider-neutral personal access
  tokens (PATs) for scripts and legacy clients. Preserve hashed-at-rest credentials, explicit actor
  attribution, operation and Space scopes, revocation, and the legacy Action compatibility surface.
- Define atomic record, revision, and audit behavior before PATs or later Connections are treated as
  a durable automation boundary. The legacy LLM upsert now commits its owner-qualified record
  create/update, revision, and required audit event through one application-owned unit of work;
  the non-durable in-memory test double's rollback and a short MongoDB session transaction provide
  equivalent all-or-nothing behavior.

### Verification criteria

- Tests cover setup/bootstrap, valid and invalid sign-in, sign-out, password changes, recovery,
  credential persistence, and refusal of insecure bootstrap paths.
- Tests cover Argon2id verification, expired/inactive/rotated sessions, CSRF failures, secure
  cookie configuration, and protected-route denial.
- Tests prove a clean local Instance starts without Firebase, OIDC, or GCP configuration.
- Repository contracts prove owner-qualified Page isolation and PAT ID/hash uniqueness, rotation,
  collision rejection, and monotonic revocation across memory and MongoDB adapters.
- Tests and UI checks prove terminology is consistent at the user boundary and legacy Record
  compatibility does not leak authorization or content.
- Run the documented app quality gates and a local browser-flow verification without relying on
  cloud credentials.

## Milestone 14: Optional Google login and hosted activation

Add Firebase/Google sign-in and generic OIDC adapters as optional dependency groups. Activate or
re-verify hosted/GCP deployment only after the portable owner-auth path is proven. Hosted identity
must map to MatrixedMind-owned users and sessions; it must not replace local authentication as the
product baseline.

Activation blockers include aligning the Terraform `AUTH_MODE`, additive owner-qualified indexes,
an explicit existing `dev-user` record/PAT ownership migration, Firestore verification of auth and
automation transactions and new auth indexes, a canonical trusted HTTPS browser-origin contract,
and shared authentication-attempt limiting. Each live infrastructure or data change remains subject
to cloud change control and exact-plan approval.

## Milestone 15: Connections and access grants

Model Connections as external actors with explicit, revocable grants. Centralize grant evaluation,
auditing, expiration, and Space/Page scope. Keep the Mind owner in control and default new grants
to no access.

## Milestone 16: Authorization-aware retrieval

Apply authorization consistently to Page reads, lists, references, search, and retrieval context.
Prove that filtering and derived metadata do not disclose inaccessible Pages or Spaces.

## Milestone 17: ChatGPT/MCP safe capture

Provide an optional MCP integration and safe capture workflow through Connection grants. Replace
the legacy Custom GPT Action/token path only after the new capability has equivalent or stronger
scoping, revocation, attribution, audit, and migration/rollback evidence. Until then the legacy
path remains supported.

## Milestone 18: Portability and archive ingestion

Implement the versioned export/import format from ADR 0009, archive ingestion, conflict handling,
and recovery verification. Preserve Page bodies, metadata, history, identity, and authorization
meaning without coupling exports to a database provider.

## Milestone 19: Public project documentation

Publish reviewed project documentation as an opt-in project activity, separate from an Instance and
its private knowledge. Maintain the source-offer and public-documentation policies already
accepted in ADRs 0016 and 0017.

## Working rules

- Roadmap milestones represent high-level product capabilities and sequencing; actionable
  implementation work is decomposed into bounded GitHub Issues.
- Issues within a milestone collectively satisfy the milestone. Verify individual issues thoroughly
  before integrating, and complete issue-level verification before declaring a milestone complete.
- Complete and verify one milestone before stacking the next.
- Add tests and repository documentation whenever behavior or a contract changes.
- Record accepted architectural decisions in ADRs under `docs/DECISIONS/`. Create GitHub Issues for
  actionable work, implementation tasks, and unresolved decisions.
- Do not extract services, packages, or repositories merely for organization; extract only when an
  independently versioned, deployed, operated, or governed lifecycle is demonstrated.
