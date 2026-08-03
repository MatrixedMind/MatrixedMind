#!/bin/sh
set -eu

fixture_dir=$(mktemp -d "${TMPDIR:-/tmp}/matrixedmind-terraform-mcp-test.XXXXXX")
trap 'rm -rf "$fixture_dir"' EXIT HUP INT TERM
test_codex="$fixture_dir/.codex"
mkdir -p "$test_codex/scripts"
cp .codex/scripts/terraform-mcp-registry-docs "$test_codex/scripts/terraform-mcp-registry-docs"
cp .codex/terraform-mcp-registry-docs.manifest.toml "$test_codex/terraform-mcp-registry-docs.manifest.toml"
wrapper="$test_codex/scripts/terraform-mcp-registry-docs"
docker_log="$fixture_dir/docker-arguments"
docker_env="$fixture_dir/docker-environment"
fake_docker="$fixture_dir/docker"

printf '%s\n' '#!/bin/sh' "env > '$docker_env'" "printf '%s\\n' \"\$@\" > '$docker_log'" > "$fake_docker"
chmod 700 "$fake_docker"
sed "s|/usr/local/bin/docker|$fake_docker|" "$wrapper" > "$wrapper.patched"
mv "$wrapper.patched" "$wrapper"

assert_failure() {
  expected=$1
  shift
  output=$("$@" 2>&1) && { echo "expected failure: $*" >&2; exit 1; }
  case "$output" in *"$expected"*) ;; *) echo "unexpected output: $output" >&2; exit 1;; esac
}

assert_failure 'rejects arguments outside' /bin/sh "$wrapper" stdio --tools=get_latest_provider_version
assert_failure 'rejects arguments outside' /bin/sh "$wrapper" 'stdio --tools=search_providers,get_provider_details'
grep -qx 'docker_bin=/usr/local/bin/docker' .codex/scripts/terraform-mcp-registry-docs
grep -Fqx 'script_dir=$(CDPATH= cd -- "$(/usr/bin/dirname -- "$0")" && /bin/pwd -P)' .codex/scripts/terraform-mcp-registry-docs

hostile_path="$fixture_dir/hostile-path"
hostile_marker="$fixture_dir/hostile-path-used"
mkdir -p "$hostile_path"
for command in dirname awk; do
  printf '%s\n' '#!/bin/sh' "touch '$hostile_marker'" 'exit 99' > "$hostile_path/$command"
  chmod 700 "$hostile_path/$command"
done

manifest_backup="$fixture_dir/manifest"
cp "$test_codex/terraform-mcp-registry-docs.manifest.toml" "$manifest_backup"
printf '%s\n' 'version = "not-approved"' > "$test_codex/terraform-mcp-registry-docs.manifest.toml"
assert_failure 'manifest does not match' /bin/sh "$wrapper" stdio --tools=search_providers,get_provider_details
cp "$manifest_backup" "$test_codex/terraform-mcp-registry-docs.manifest.toml"

AWS_SECRET_ACCESS_KEY=not-forwarded \
TF_TOKEN_app_terraform_io=not-forwarded \
HCP_CLIENT_SECRET=not-forwarded \
DOCKER_CONFIG=not-forwarded \
PATH="$hostile_path" \
/bin/sh "$wrapper" stdio --tools=search_providers,get_provider_details
[ ! -e "$hostile_marker" ]

expected="$fixture_dir/expected"
cat > "$expected" <<'EOF'
run
--rm
-i
--platform
linux/arm64
--cap-drop
ALL
--security-opt
no-new-privileges:true
--read-only
hashicorp/terraform-mcp-server@sha256:312d63756b5474df384b1844af55b58ca48cbe0996871e1d6c4239bfcd6fcd29
stdio
--tools=search_providers,get_provider_details
EOF
cmp -s "$expected" "$docker_log" || { echo 'Docker hardening invocation did not match the approved command.' >&2; exit 1; }
grep -qx 'PATH=/usr/bin:/bin:/usr/sbin:/sbin' "$docker_env"
grep -Eq '^DOCKER_CONFIG=.*/matrixedmind-terraform-mcp-docker\.[^/]+$' "$docker_env"
if grep -qx 'DOCKER_CONFIG=not-forwarded' "$docker_env"; then
  echo 'Docker client inherited the caller Docker config.' >&2
  exit 1
fi
for forbidden in AWS_SECRET_ACCESS_KEY TF_TOKEN_app_terraform_io HCP_CLIENT_SECRET; do
  if grep -q "^$forbidden=" "$docker_env"; then
    echo "Docker client inherited forbidden environment variable: $forbidden" >&2
    exit 1
  fi
done

echo 'Terraform MCP container wrapper tests passed'
