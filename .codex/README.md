# Codex agent integrations

## Terraform Registry documentation MCP

`gcp_docs_researcher` may use only HashiCorp's public Terraform MCP Server
v1.1.0 container and only `search_providers` and `get_provider_details`.
HashiCorp did not publish a supported macOS ARM64 v1.1.0 release artifact, so a
local binary is not an approved fallback. The checked-in manifest pins the
multi-platform image index exactly to
`hashicorp/terraform-mcp-server@sha256:312d63756b5474df384b1844af55b58ca48cbe0996871e1d6c4239bfcd6fcd29`
and records its reviewed `linux/arm64` child digest
`sha256:2b18f06858bb7b0cd7d0a297344ffb00ad5d6c7d22750f9a78a6d914523d1a9e`.

The wrapper accepts only `stdio --tools=search_providers,get_provider_details`,
validates those checked-in constants, uses a private empty Docker client config
so the public-image pull cannot consult host credential helpers, and launches
the image with Docker's fixed `linux/arm64` platform, a read-only filesystem,
all Linux capabilities dropped, and `no-new-privileges`. It passes no
environment variables or host mounts to the container, clears the Docker
client's inherited environment, and never downloads or installs a binary. It
deliberately omits
`get_latest_provider_version`, private Registry credentials, HCP Terraform,
Terraform Enterprise, workspace, run-management, and mutation tools.

For v1.1.0, call `search_providers` with these string properties:
`provider_document_type` (such as `resources`, `data-sources`, `functions`,
`guides`, or `overview`), `provider_name`, `provider_namespace`,
`service_slug`, and the relevant exact `provider_version` when available. Then
pass the returned exact string `provider_doc_id` as the sole
`get_provider_details` property. This two-step lookup avoids guessing an
internal document identifier.

For provider questions, `.terraform.lock.hcl` remains the authority for the
version actually in use. The development root locks `hashicorp/google` at
`7.41.0`; the production and edge roots lock it at `7.42.0` (the bootstrap root
has its independent `7.39.0` lock). Retrieve documentation for the relevant
locked version whenever possible rather than treating a current Registry answer
as deployment evidence.

## GCP observer MCP

`matrixedmind_gcp_observer` uses the local standard-library stdio server at
`.codex/scripts/gcp-observer-mcp`. Its complete allowlist is Cloud Logging
`list_log_entries` and `list_log_names`; Cloud Monitoring `list_timeseries`,
`query_range`, `get_alert_policy`, `list_alert_policies`, and
`list_metric_descriptors`; and Cloud Run `get_service` and `list_services`.
It has no generic HTTP, gcloud-command, IAM, Secret Manager, Firestore,
deployment, credential, or mutation tool. Incident APIs are deliberately not
offered because this bounded server does not support them.

The launcher clears the inherited environment except for the required
non-secret operator-email assertion and starts the system Python with isolated,
environment-ignoring flags. The server separately invokes only its two exact
gcloud ADC token commands with a reconstructed minimal environment.

Every call must give an exact matching environment/project pair
(`development`/`matrixed-mind-dev` or `production`/`matrixedmind-prod`), a
concrete objective, UTC RFC3339 start/end timestamps no more than six hours
apart, and a limit from 1 through 100. The shared-edge project is excluded.
Before a metric-descriptor or time-series query, the server reads the selected
project's Metrics Scope and fails closed unless it contains exactly that project
as a non-tombstoned member; this prevents a future cross-project Metrics Scope
attachment from silently widening observer access.
List operations use that fixed limit only: caller page tokens are rejected, and
the Logging log-name collection path URL-encodes the fixed approved project ID.
`list_log_entries` always ANDs server-generated inclusive timestamp bounds with
any supplied Logging filter, so its API request cannot escape the requested
window. `query_range` injects the fixed project, validated start/end, a 60-second
step, and a 20-second timeout into the Managed Prometheus range endpoint. Google
does not provide a server-side series-limit parameter for that endpoint, so the
server caps the sanitized MCP result to the requested limit and reports whether
additional series were truncated.
The server uses source ADC only to call Google userinfo and verify that its
email equals the required local `MATRIXEDMIND_GCP_OPERATOR_EMAIL`; it then
uses `gcloud auth application-default print-access-token` with the conventional
environment observer service account (`matrixedmind-dev-observer` or
`matrixedmind-prod-observer`) for the read-only REST call. It never prints
tokens, headers, environment values,
or raw log/event payloads. Results are reduced to sanitized metadata.

No service account, credentials, API enablement, or IAM role is created by
this repository configuration. Those live prerequisites remain subject to the
separately approved audited cloud-mutation plan and must grant only the
observer's documented read roles.
