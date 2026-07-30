#!/bin/sh
set -eu

if [ "$(/usr/bin/uname -s)" != 'Darwin' ] || [ "$(/usr/bin/uname -m)" != 'arm64' ]; then
  echo 'Skipping Terraform MCP wrapper failure-mode tests: requires Darwin arm64'
  exit 0
fi

wrapper=.codex/scripts/terraform-mcp-registry-docs
assert_failure() {
  expected=$1
  shift
  output=$("$@" 2>&1) && { echo "expected failure: $*" >&2; exit 1; }
  case "$output" in *"$expected"*) ;; *) echo "unexpected output: $output" >&2; exit 1;; esac
}

assert_failure 'Set MATRIXEDMIND_TERRAFORM_MCP_ARCHIVE' env -u MATRIXEDMIND_TERRAFORM_MCP_ARCHIVE -u MATRIXEDMIND_TERRAFORM_MCP_BINARY sh "$wrapper" stdio --tools=search_providers,get_provider_details

fixture_dir=$(mktemp -d "${TMPDIR:-/tmp}/matrixedmind-terraform-mcp-test.XXXXXX")
trap 'rm -rf "$fixture_dir"' EXIT HUP INT TERM
fake_archive="$fixture_dir/terraform-mcp-server_1.1.0_darwin_arm64.zip"
fake_binary="$fixture_dir/terraform-mcp-server"
printf 'tampered archive' > "$fake_archive"
printf '#!/bin/sh\necho 1.1.0\n' > "$fake_binary"
chmod 700 "$fake_binary"
assert_failure 'binary is missing or not executable' env MATRIXEDMIND_TERRAFORM_MCP_ARCHIVE="$fake_archive" MATRIXEDMIND_TERRAFORM_MCP_BINARY="$fixture_dir/missing-binary" sh "$wrapper" stdio --tools=search_providers,get_provider_details
assert_failure 'archive checksum does not match' env MATRIXEDMIND_TERRAFORM_MCP_ARCHIVE="$fake_archive" MATRIXEDMIND_TERRAFORM_MCP_BINARY="$fake_binary" sh "$wrapper" stdio --tools=search_providers,get_provider_details

assert_failure 'rejects arguments outside' sh "$wrapper" stdio --tools=get_latest_provider_version

# Create an isolated, checksum-patched copy of the wrapper to exercise a full
# launch without requiring the real HashiCorp artifact. It proves that hostile
# PATH tools are ignored and that env -i strips inherited credentials.
test_codex="$fixture_dir/agent-root/.codex"
mkdir -p "$test_codex/scripts" "$fixture_dir/archive-contents" "$fixture_dir/hostile-bin"
result_file="$fixture_dir/binary-result"
trusted_binary="$fixture_dir/archive-contents/terraform-mcp-server"
printf '%s\n' '#!/bin/sh' 'if [ "${MATRIXEDMIND_TEST_SENTINEL+x}" = x ]; then' "  printf '%s\\n' leaked > '$result_file'" '  exit 91' 'fi' "printf '%s\\n' \"\$*\" > '$result_file'" 'if [ "${1:-}" = "--version" ]; then echo 1.1.0; fi' > "$trusted_binary"
chmod 700 "$trusted_binary"
verified_archive="$fixture_dir/terraform-mcp-server_1.1.0_darwin_arm64.zip"
/bin/rm -f "$verified_archive"
(cd "$fixture_dir/archive-contents" && /usr/bin/zip -q "$verified_archive" terraform-mcp-server)
installed_binary="$fixture_dir/installed-terraform-mcp-server"
cp "$trusted_binary" "$installed_binary"
chmod 700 "$installed_binary"
verified_sha=$(/usr/bin/shasum -a 256 "$verified_archive" | /usr/bin/awk '{print $1}')
/usr/bin/sed "s/741e7175224a54fcef1c132c272a3fbf9362f4fc00469ae2c370b8c2ae8f3ef8/$verified_sha/g" "$wrapper" > "$test_codex/scripts/terraform-mcp-registry-docs"
/usr/bin/sed "s/741e7175224a54fcef1c132c272a3fbf9362f4fc00469ae2c370b8c2ae8f3ef8/$verified_sha/g" .codex/terraform-mcp-registry-docs.manifest.toml > "$test_codex/terraform-mcp-registry-docs.manifest.toml"
marker="$fixture_dir/hostile-path-used"
printf '%s\n' '#!/bin/sh' "printf '%s\\n' used > '$marker'" > "$fixture_dir/hostile-bin/shasum"
printf '%s\n' '#!/bin/sh' "printf '%s\\n' used > '$marker'" > "$fixture_dir/hostile-bin/unzip"
printf '%s\n' '#!/bin/sh' "printf '%s\\n' used > '$marker'" > "$fixture_dir/hostile-bin/env"
chmod 700 "$fixture_dir/hostile-bin/shasum" "$fixture_dir/hostile-bin/unzip" "$fixture_dir/hostile-bin/env"
MATRIXEDMIND_TEST_SENTINEL='must-not-reach-binary' PATH="$fixture_dir/hostile-bin:$PATH" MATRIXEDMIND_TERRAFORM_MCP_ARCHIVE="$verified_archive" MATRIXEDMIND_TERRAFORM_MCP_BINARY="$installed_binary" /bin/sh "$test_codex/scripts/terraform-mcp-registry-docs" stdio --tools=search_providers,get_provider_details
[ ! -e "$marker" ]
[ "$(cat "$result_file")" = 'stdio --tools=search_providers,get_provider_details' ]

# Replace the external archive after the wrapper has made its private copy.
# A vulnerable wrapper that later unzips the external path would launch the
# malicious binary; the hardened wrapper must launch the trusted private copy.
race_tmp="$fixture_dir/race-tmp"
mkdir "$race_tmp" "$fixture_dir/malicious-contents"
/bin/dd if=/dev/zero of="$fixture_dir/archive-contents/filler" bs=1048576 count=48 2>/dev/null
/bin/rm -f "$verified_archive"
(cd "$fixture_dir/archive-contents" && /usr/bin/zip -q -0 "$verified_archive" terraform-mcp-server filler)
verified_sha=$(/usr/bin/shasum -a 256 "$verified_archive" | /usr/bin/awk '{print $1}')
/usr/bin/sed "s/741e7175224a54fcef1c132c272a3fbf9362f4fc00469ae2c370b8c2ae8f3ef8/$verified_sha/g" "$wrapper" > "$test_codex/scripts/terraform-mcp-registry-docs"
/usr/bin/sed "s/741e7175224a54fcef1c132c272a3fbf9362f4fc00469ae2c370b8c2ae8f3ef8/$verified_sha/g" .codex/terraform-mcp-registry-docs.manifest.toml > "$test_codex/terraform-mcp-registry-docs.manifest.toml"
printf '%s\n' '#!/bin/sh' "printf '%s\\n' malicious > '$result_file'" 'if [ "${1:-}" = "--version" ]; then echo 1.1.0; fi' > "$fixture_dir/malicious-contents/terraform-mcp-server"
chmod 700 "$fixture_dir/malicious-contents/terraform-mcp-server"
malicious_archive="$fixture_dir/malicious-archive.zip"
(cd "$fixture_dir/malicious-contents" && /usr/bin/zip -q "$malicious_archive" terraform-mcp-server)
MATRIXEDMIND_TEST_SENTINEL='must-not-reach-binary' TMPDIR="$race_tmp" MATRIXEDMIND_TERRAFORM_MCP_ARCHIVE="$verified_archive" MATRIXEDMIND_TERRAFORM_MCP_BINARY="$installed_binary" /bin/sh "$test_codex/scripts/terraform-mcp-registry-docs" stdio --tools=search_providers,get_provider_details &
race_pid=$!
private_copy=''
attempt=0
while [ "$attempt" -lt 500 ]; do
  for candidate in "$race_tmp"/matrixedmind-terraform-mcp.*/terraform-mcp-server_1.1.0_darwin_arm64.zip; do
    if [ -f "$candidate" ]; then
      private_copy=$candidate
      break 2
    fi
  done
  /bin/sleep 0.01
  attempt=$((attempt + 1))
done
if [ -z "$private_copy" ]; then
  kill "$race_pid" 2>/dev/null || true
  wait "$race_pid" 2>/dev/null || true
  echo 'wrapper did not create a private archive copy' >&2
  exit 1
fi
/bin/mv "$malicious_archive" "$verified_archive"
wait "$race_pid"
[ "$(cat "$result_file")" = 'stdio --tools=search_providers,get_provider_details' ]

# Restore a verified archive before exercising the installed-binary mismatch
# branch; the race deliberately replaced the external archive with a malicious
# one and must not mask this independent fail-closed assertion.
/bin/rm -f "$verified_archive"
(cd "$fixture_dir/archive-contents" && /usr/bin/zip -q -0 "$verified_archive" terraform-mcp-server filler)
verified_sha=$(/usr/bin/shasum -a 256 "$verified_archive" | /usr/bin/awk '{print $1}')
/usr/bin/sed "s/741e7175224a54fcef1c132c272a3fbf9362f4fc00469ae2c370b8c2ae8f3ef8/$verified_sha/g" "$wrapper" > "$test_codex/scripts/terraform-mcp-registry-docs"
/usr/bin/sed "s/741e7175224a54fcef1c132c272a3fbf9362f4fc00469ae2c370b8c2ae8f3ef8/$verified_sha/g" .codex/terraform-mcp-registry-docs.manifest.toml > "$test_codex/terraform-mcp-registry-docs.manifest.toml"
printf '#!/bin/sh\necho wrong 1.1.0\n' > "$installed_binary"
chmod 700 "$installed_binary"
assert_failure 'binary does not match the approved archive' env MATRIXEDMIND_TERRAFORM_MCP_ARCHIVE="$verified_archive" MATRIXEDMIND_TERRAFORM_MCP_BINARY="$installed_binary" /bin/sh "$test_codex/scripts/terraform-mcp-registry-docs" stdio --tools=search_providers,get_provider_details

echo 'Terraform MCP wrapper failure-mode tests passed'
