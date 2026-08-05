from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
GUARD = REPO_ROOT / ".codex" / "scripts" / "terraform-plan-scope-guard"


def resource_change(
    address: str,
    actions: list[str],
    *,
    mode: str = "managed",
    resource_type: str = "google_cloud_run_v2_service",
    previous_address: str | None = None,
    importing: bool = False,
    unknown: bool = False,
    sensitive: bool = False,
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "address": address,
        "mode": mode,
        "type": resource_type,
        "name": "this",
        "provider_name": "registry.terraform.io/hashicorp/google",
        "change": {
            "actions": actions,
            "before": {"secret_data": "DO_NOT_PRINT"} if sensitive else {},
            "after": {"secret_data": "DO_NOT_PRINT"} if sensitive else {},
            "after_unknown": {"computed": True} if unknown else {},
            "before_sensitive": {},
            "after_sensitive": {"secret_data": True} if sensitive else {},
        },
    }
    if previous_address is not None:
        result["previous_address"] = previous_address
    if importing:
        result["change"]["importing"] = {"id": "redacted-fixture-id"}
    return result


def output_change(
    actions: list[str],
    *,
    unknown: bool = False,
    before_sensitive: bool = False,
    after_sensitive: bool = False,
) -> dict[str, Any]:
    return {
        "actions": actions,
        "before": "DO_NOT_PRINT" if before_sensitive else None,
        "after": "DO_NOT_PRINT" if before_sensitive or after_sensitive else None,
        "after_unknown": unknown,
        "before_sensitive": before_sensitive,
        "after_sensitive": after_sensitive,
    }


def plan(
    *changes: dict[str, Any],
    drift: list[dict[str, Any]] | None = None,
    outputs: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    return {
        "format_version": "1.2",
        "terraform_version": "1.9.0",
        "applyable": bool(changes or outputs),
        "complete": True,
        "errored": False,
        "resource_changes": list(changes),
        "resource_drift": drift or [],
        "output_changes": outputs or {},
    }


def scope(
    *entries: dict[str, Any],
    drift: list[dict[str, Any]] | None = None,
    outputs: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    return {
        "scope_version": 1,
        "allowed_changes": list(entries),
        "allowed_drift": drift or [],
        "allowed_outputs": outputs or [],
    }


class TerraformPlanScopeGuardTests(unittest.TestCase):
    def run_guard(self, plan_value: Any, scope_value: Any) -> subprocess.CompletedProcess[str]:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            plan_path = root / "plan.json"
            scope_path = root / "scope.json"
            plan_path.write_text(json.dumps(plan_value), encoding="utf-8")
            scope_path.write_text(json.dumps(scope_value), encoding="utf-8")
            return subprocess.run(
                [str(GUARD), str(plan_path), "--scope", str(scope_path)],
                check=False,
                capture_output=True,
                text=True,
            )

    def test_allowed_only_plan_passes(self) -> None:
        address = "module.service.google_cloud_run_v2_service.this"
        result = self.run_guard(
            plan(resource_change(address, ["update"])),
            scope({"address": address, "actions": ["update"]}),
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("PASS:", result.stdout)
        self.assertIn("cloud-run", result.stdout)

    def test_unexpected_high_risk_updates_fail_and_flag_domains(self) -> None:
        cases = {
            "cloud-run": "google_cloud_run_v2_service",
            "iam": "google_project_iam_member",
            "secret": "google_secret_manager_secret",
            "database": "google_firestore_database",
            "budget": "google_billing_budget_budget",
            "alert": "google_monitoring_alert_policy",
            "edge": "google_compute_global_forwarding_rule",
            "deployment": "google_artifact_registry_repository",
            "api": "google_project_service",
        }
        for domain, resource_type in cases.items():
            with self.subTest(domain=domain):
                address = f"{resource_type}.unexpected"
                result = self.run_guard(
                    plan(resource_change(address, ["update"], resource_type=resource_type)),
                    scope(),
                )
                self.assertEqual(result.returncode, 1)
                self.assertIn("unexpected change", result.stderr)
                self.assertIn(f"[{domain}]", result.stderr)

    def test_destroy_requires_exact_approval(self) -> None:
        address = "google_secret_manager_secret.runtime"
        result = self.run_guard(
            plan(
                resource_change(address, ["delete"], resource_type="google_secret_manager_secret")
            ),
            scope({"address": address, "actions": ["update"]}),
        )
        self.assertEqual(result.returncode, 1)
        self.assertIn("expected update; observed delete", result.stderr)

    def test_replace_is_classified_independently(self) -> None:
        address = "google_firestore_database.app"
        result = self.run_guard(
            plan(
                resource_change(
                    address, ["delete", "create"], resource_type="google_firestore_database"
                )
            ),
            scope({"address": address, "actions": ["replace"]}),
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("replace=1", result.stdout)

    def test_sensitive_and_unknown_require_per_address_opt_in(self) -> None:
        address = "google_secret_manager_secret_version.runtime"
        plan_value = plan(
            resource_change(
                address,
                ["create"],
                resource_type="google_secret_manager_secret_version",
                unknown=True,
                sensitive=True,
            )
        )
        denied = self.run_guard(
            plan_value,
            scope({"address": address, "actions": ["create"]}),
        )
        self.assertEqual(denied.returncode, 1)
        self.assertIn("unapproved unknown", denied.stderr)
        self.assertIn("unapproved sensitive", denied.stderr)
        self.assertNotIn("DO_NOT_PRINT", denied.stdout + denied.stderr)

        allowed = self.run_guard(
            plan_value,
            scope(
                {
                    "address": address,
                    "actions": ["create"],
                    "allow_unknown": True,
                    "allow_sensitive": True,
                }
            ),
        )
        self.assertEqual(allowed.returncode, 0, allowed.stderr)
        self.assertNotIn("DO_NOT_PRINT", allowed.stdout + allowed.stderr)

    def test_output_create_update_and_delete_require_exact_approval(self) -> None:
        for action in ("create", "update", "delete"):
            with self.subTest(action=action):
                plan_value = plan(
                    outputs={
                        "runtime_endpoint": output_change(
                            [action],
                            before_sensitive=action != "create",
                            after_sensitive=action != "delete",
                        )
                    }
                )
                denied = self.run_guard(plan_value, scope())
                self.assertEqual(denied.returncode, 1)
                self.assertIn("unexpected output runtime_endpoint", denied.stderr)
                self.assertNotIn("DO_NOT_PRINT", denied.stdout + denied.stderr)

                allowed = self.run_guard(
                    plan_value,
                    scope(
                        outputs=[
                            {
                                "name": "runtime_endpoint",
                                "actions": [action],
                                "allow_sensitive": True,
                            }
                        ]
                    ),
                )
                self.assertEqual(allowed.returncode, 0, allowed.stderr)
                self.assertNotIn("DO_NOT_PRINT", allowed.stdout + allowed.stderr)

    def test_output_unknown_and_sensitive_downgrade_require_opt_in(self) -> None:
        plan_value = plan(
            outputs={
                "runtime_secret": output_change(
                    ["update"], unknown=True, before_sensitive=True, after_sensitive=False
                )
            }
        )
        denied = self.run_guard(
            plan_value,
            scope(
                outputs=[
                    {
                        "name": "runtime_secret",
                        "actions": ["update"],
                        "allow_sensitive": True,
                    }
                ]
            ),
        )
        self.assertEqual(denied.returncode, 1)
        self.assertIn("unapproved unknown values", denied.stderr)
        self.assertIn("unapproved sensitive downgrade", denied.stderr)
        self.assertNotIn("DO_NOT_PRINT", denied.stdout + denied.stderr)

        allowed = self.run_guard(
            plan_value,
            scope(
                outputs=[
                    {
                        "name": "runtime_secret",
                        "actions": ["update"],
                        "allow_unknown": True,
                        "allow_sensitive": True,
                        "allow_sensitive_downgrade": True,
                    }
                ]
            ),
        )
        self.assertEqual(allowed.returncode, 0, allowed.stderr)
        self.assertIn("output_sensitive_downgrade=1", allowed.stdout)
        self.assertNotIn("DO_NOT_PRINT", allowed.stdout + allowed.stderr)

    def test_import_and_state_move_are_explicit(self) -> None:
        imported = "google_monitoring_alert_policy.imported"
        moved = "module.new.google_billing_budget_budget.this"
        old = "google_billing_budget_budget.old"
        moved_data = "data.google_client_config.current"
        old_data = "data.google_client_config.old"
        result = self.run_guard(
            plan(
                resource_change(
                    imported,
                    ["create"],
                    resource_type="google_monitoring_alert_policy",
                    importing=True,
                ),
                resource_change(
                    moved,
                    ["no-op"],
                    resource_type="google_billing_budget_budget",
                    previous_address=old,
                ),
                resource_change(
                    moved_data,
                    ["read"],
                    mode="data",
                    resource_type="google_client_config",
                    previous_address=old_data,
                ),
            ),
            scope(
                {"address": imported, "actions": ["create", "import"]},
                {"address": moved, "actions": ["state-move"], "previous_address": old},
                {
                    "address": moved_data,
                    "actions": ["state-move"],
                    "previous_address": old_data,
                },
            ),
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("import=1", result.stdout)
        self.assertIn("state-move=2", result.stdout)

    def test_unapproved_drift_fails(self) -> None:
        address = "google_compute_url_map.shared_edge"
        result = self.run_guard(
            plan(
                drift=[resource_change(address, ["update"], resource_type="google_compute_url_map")]
            ),
            scope(),
        )
        self.assertEqual(result.returncode, 1)
        self.assertIn("unexpected drift", result.stderr)
        self.assertIn("[edge]", result.stderr)

    def test_malformed_or_unsupported_plan_fails_closed(self) -> None:
        malformed = self.run_guard({"format_version": "2.0"}, scope())
        self.assertEqual(malformed.returncode, 2)
        self.assertIn("unsupported Terraform plan JSON format major", malformed.stderr)

        deferred = self.run_guard(
            {**plan(), "deferred_changes": [{"reason": "fixture"}]},
            scope(),
        )
        self.assertEqual(deferred.returncode, 2)
        self.assertIn("deferred_changes are unsupported", deferred.stderr)

        invalid_marker_plan = plan(resource_change("google_cloud_run_v2_service.app", ["update"]))
        invalid_marker_plan["resource_changes"][0]["change"]["after_unknown"] = "yes"
        invalid_marker = self.run_guard(
            invalid_marker_plan,
            scope(
                {
                    "address": "google_cloud_run_v2_service.app",
                    "actions": ["update"],
                    "allow_unknown": True,
                }
            ),
        )
        self.assertEqual(invalid_marker.returncode, 2)
        self.assertIn("unsupported marker value", invalid_marker.stderr)

        invalid_mode_plan = plan(resource_change("google_cloud_run_v2_service.app", ["update"]))
        invalid_mode_plan["resource_changes"][0]["mode"] = {}
        invalid_mode = self.run_guard(invalid_mode_plan, scope())
        self.assertEqual(invalid_mode.returncode, 2)
        self.assertIn("mode must be managed or data", invalid_mode.stderr)

        invalid_scope_version = self.run_guard(plan(), {**scope(), "scope_version": True})
        self.assertEqual(invalid_scope_version.returncode, 2)
        self.assertIn("unsupported scope_version", invalid_scope_version.stderr)

    def test_empty_plan_passes_only_with_empty_scope(self) -> None:
        empty = self.run_guard(plan(), scope())
        self.assertEqual(empty.returncode, 0, empty.stderr)
        self.assertIn("changes=0", empty.stdout)

        unused = self.run_guard(
            plan(),
            scope({"address": "google_cloud_run_v2_service.app", "actions": ["update"]}),
        )
        self.assertEqual(unused.returncode, 1)
        self.assertIn("allowed change missing from plan", unused.stderr)


if __name__ == "__main__":
    unittest.main()
