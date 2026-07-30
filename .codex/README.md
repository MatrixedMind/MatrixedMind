# Codex agent integrations

## Terraform Registry documentation MCP

`gcp_docs_researcher` may use only the user-installed local
`terraform-mcp-server` v1.1.0 binary and only its `search_providers` and
`get_provider_details` tools. The checked-in wrapper accepts precisely the
`stdio --tools=search_providers,get_provider_details` invocation, copies the
external archive into private temporary storage before verification, extracts
and copies its verified binary there, and launches that same copy for its
version check and MCP session with a cleared environment. The
configuration deliberately omits
`get_latest_provider_version`, private-registry credentials, HCP Terraform,
Terraform Enterprise, workspace, run-management, and mutation tools.

Do not place the binary, credentials, or a guessed checksum in this repository.
The approved local platform is macOS ARM64. Its manifest records the public
HashiCorp archive name, source URL, and SHA-256. Store both the archive and the
installed binary outside this repository, then set
`MATRIXEDMIND_TERRAFORM_MCP_ARCHIVE` and
`MATRIXEDMIND_TERRAFORM_MCP_BINARY` to their absolute paths. The wrapper fails
closed unless the archive checksum matches the manifest, the installed binary
matches the verified archive's extracted binary, and its version reports 1.1.0.
It does not download or install anything.

Before first use, independently compare the archive with HashiCorp's published
checksum file and verify the installed binary version:

```sh
shasum -a 256 -c --ignore-missing terraform-mcp-server_1.1.0_SHA256SUMS
"$MATRIXEDMIND_TERRAFORM_MCP_BINARY" --version
```

The selected archive must match the official checksum for the exact v1.1.0
platform artifact, and the version command must report v1.1.0. The source
manifest is reviewed static metadata, not an installation record. For provider
questions, `.terraform.lock.hcl` remains the authority for the version actually
in use; retrieve locked-version provider documentation whenever possible.

## GCP observer MCP

The `matrixedmind_gcp_observer` agent is intentionally an instruction-only
read-only boundary. It has no GCP MCP endpoint, service account, credentials,
or live project access configured. Adding any endpoint, enabling APIs, or
granting IAM requires the user's separate explicit approval of the audited
cloud-mutation plan.
