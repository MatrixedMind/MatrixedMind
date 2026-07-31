"""No-live-cloud contract tests for the MatrixedMind observer MCP server."""

from __future__ import annotations

import importlib.machinery
import importlib.util
import json
import os
import subprocess
import tempfile
import unittest
import urllib.error
from pathlib import Path
from unittest.mock import Mock, patch

SCRIPT = Path(__file__).parents[1] / "scripts" / "gcp-observer-mcp"
loader = importlib.machinery.SourceFileLoader("gcp_observer_mcp", str(SCRIPT))
spec = importlib.util.spec_from_loader(loader.name, loader)
observer = importlib.util.module_from_spec(spec)
loader.exec_module(observer)

VALID = {
    "environment": "development",
    "project_id": "matrixed-mind-dev",
    "start_time": "2026-07-31T12:00:00Z",
    "end_time": "2026-07-31T12:30:00Z",
    "objective": "Check recent Cloud Run errors",
    "limit": 10,
}


class ObserverMcpTests(unittest.TestCase):
    def test_tool_list_is_exact_and_has_required_boundary_inputs(self) -> None:
        tools = [observer.tool_schema(name) for name in observer.TOOLS]
        self.assertEqual([tool["name"] for tool in tools], list(observer.TOOLS))
        self.assertEqual(len(tools), 9)
        self.assertNotIn("get_alert", observer.TOOLS)
        self.assertNotIn("create_alert_policy", observer.TOOLS)
        for tool in tools:
            schema = tool["inputSchema"]
            self.assertTrue(schema["additionalProperties"] is False)
            self.assertEqual(schema["properties"]["environment"]["type"], "string")
            self.assertEqual(schema["properties"]["project_id"]["type"], "string")
            self.assertEqual(schema["properties"]["start_time"]["type"], "string")
            self.assertEqual(schema["properties"]["end_time"]["type"], "string")
            self.assertEqual(schema["properties"]["objective"]["type"], "string")
        self.assertEqual(tools[2]["inputSchema"]["required"], [*observer.COMMON_REQUIRED, "filter"])
        self.assertEqual(tools[3]["inputSchema"]["required"], [*observer.COMMON_REQUIRED, "query"])
        self.assertEqual(
            tools[4]["inputSchema"]["required"], [*observer.COMMON_REQUIRED, "alert_policy_id"]
        )
        self.assertEqual(
            tools[7]["inputSchema"]["required"], [*observer.COMMON_REQUIRED, "service_name"]
        )
        self.assertEqual(
            tools[8]["inputSchema"]["required"], [*observer.COMMON_REQUIRED, "location"]
        )

    def test_rejects_unknown_mutation_and_bad_bounds(self) -> None:
        with self.assertRaisesRegex(observer.ObserverError, "allowlist"):
            observer.validate("delete_service", VALID)
        for bad in (
            {"project_id": "matrixedmind-prod"},
            {"end_time": "2026-07-31T19:00:01Z"},
            {"limit": 101},
        ):
            with self.subTest(bad=bad), self.assertRaises(observer.ObserverError):
                observer.validate("list_log_entries", VALID | bad)

    def test_rejects_missing_tool_specific_or_arbitrary_arguments(self) -> None:
        for name, _argument in (
            ("list_timeseries", "filter"),
            ("query_range", "query"),
            ("get_alert_policy", "alert_policy_id"),
            ("get_service", "service_name"),
            ("list_services", "location"),
        ):
            with self.subTest(name=name), self.assertRaisesRegex(observer.ObserverError, "missing"):
                observer.validate(name, VALID)
        with self.assertRaisesRegex(observer.ObserverError, "Unexpected"):
            observer.validate("list_log_names", VALID | {"pageToken": "unbounded"})

    @patch.object(observer.os, "access", return_value=True)
    @patch.object(observer.subprocess, "run", return_value=Mock(stdout="short-lived-token"))
    def test_credential_command_has_exact_allowlist_and_clean_environment(
        self, run: Mock, _: Mock
    ) -> None:
        self.assertEqual(
            observer.command_token(["auth", "application-default", "print-access-token"]),
            "short-lived-token",
        )
        command = run.call_args.args[0]
        environment = run.call_args.kwargs["env"]
        self.assertEqual(command[1:], ["auth", "application-default", "print-access-token"])
        self.assertNotIn("HTTPS_PROXY", environment)
        self.assertNotIn("GOOGLE_APPLICATION_CREDENTIALS", environment)
        with self.assertRaisesRegex(observer.ObserverError, "outside"):
            observer.command_token(["projects", "delete", "matrixed-mind-dev"])

    @patch.dict(
        os.environ, {"MATRIXEDMIND_GCP_OPERATOR_EMAIL": "operator@example.test"}, clear=True
    )
    @patch.object(
        observer,
        "command_token",
        side_effect=["source-token-should-never-leak", "impersonated-token-should-never-leak"],
    )
    @patch.object(observer, "fetch_json")
    def test_log_result_is_sanitized_and_tokens_do_not_cross_boundary(
        self, fetch_json: object, _: object
    ) -> None:
        fetch_json.side_effect = [
            {"email": "operator@example.test"},
            {
                "entries": [
                    {
                        "timestamp": "2026-07-31T12:00:01Z",
                        "severity": "ERROR",
                        "logName": "projects/matrixed-mind-dev/logs/run.googleapis.com%2Fstderr",
                        "resource": {"type": "cloud_run_revision"},
                        "textPayload": "Bearer source-token-should-never-leak",
                        "jsonPayload": {"secret": "no"},
                    }
                ]
            },
        ]
        result = observer.observe("list_log_entries", VALID)
        rendered = json.dumps(result)
        self.assertIn("cloud_run_revision", rendered)
        self.assertNotIn("source-token-should-never-leak", rendered)
        self.assertNotIn("impersonated-token-should-never-leak", rendered)
        self.assertNotIn("textPayload", rendered)
        self.assertNotIn("jsonPayload", rendered)

    @patch.dict(
        os.environ, {"MATRIXEDMIND_GCP_OPERATOR_EMAIL": "operator@example.test"}, clear=True
    )
    @patch.object(observer, "command_token", side_effect=["source-token", "impersonated-token"])
    @patch.object(
        observer, "fetch_json", side_effect=[{"email": "operator@example.test"}, {"entries": []}]
    )
    def test_log_entries_inject_exact_timestamp_bounds(self, fetch_json: object, _: object) -> None:
        observer.observe("list_log_entries", VALID | {"filter": "severity>=ERROR"})
        body = fetch_json.call_args_list[1].kwargs["body"]
        self.assertEqual(
            body["filter"],
            '(severity>=ERROR) AND timestamp >= "2026-07-31T12:00:00Z" '
            'AND timestamp <= "2026-07-31T12:30:00Z"',
        )
        self.assertEqual(body["pageSize"], 10)
        self.assertNotIn("pageToken", body)
        self.assertEqual(
            observer.log_names_url("matrixed-mind-dev", 10),
            "https://logging.googleapis.com/v2/projects/matrixed-mind-dev/logs?pageSize=10",
        )

    @patch.dict(
        os.environ, {"MATRIXEDMIND_GCP_OPERATOR_EMAIL": "operator@example.test"}, clear=True
    )
    @patch.object(observer, "command_token", return_value="token")
    @patch.object(observer, "fetch_json", return_value={"email": "other@example.com"})
    def test_source_adc_identity_mismatch_fails_closed(self, _: object, __: object) -> None:
        with self.assertRaisesRegex(observer.ObserverError, "does not match"):
            observer.observer_token("matrixed-mind-dev")

    @patch.dict(
        os.environ, {"MATRIXEDMIND_GCP_OPERATOR_EMAIL": "operator@example.test"}, clear=True
    )
    @patch.object(observer, "command_token", side_effect=["source-token", "impersonated-token"])
    @patch.object(
        observer,
        "fetch_json",
        side_effect=[
            {"email": "operator@example.test"},
            {
                "name": "locations/global/metricsScopes/123",
                "monitoredProjects": [
                    {"name": "locations/global/metricsScopes/123/projects/123"},
                ],
            },
            {
                "status": "success",
                "data": {
                    "result": [
                        {
                            "metric": {
                                "__name__": "run.googleapis.com/request_count",
                                "service_name": "sensitive",
                            },
                            "values": [[1, "2"]],
                        },
                        {
                            "metric": {"__name__": "run.googleapis.com/request_count"},
                            "values": [[1, "3"]],
                        },
                    ]
                },
            },
        ],
    )
    def test_query_range_injects_bounds_and_caps_sanitized_result(
        self, fetch_json: object, _: object
    ) -> None:
        result = observer.observe("query_range", VALID | {"query": "up", "limit": 1})
        request_url = fetch_json.call_args_list[2].args[0]
        parsed = observer.urllib.parse.urlsplit(request_url)
        query = observer.urllib.parse.parse_qs(parsed.query)
        self.assertEqual(
            parsed.path,
            "/v1/projects/matrixed-mind-dev/location/global/prometheus/api/v1/query_range",
        )
        self.assertEqual(
            query,
            {
                "query": ["up"],
                "start": [VALID["start_time"]],
                "end": [VALID["end_time"]],
                "step": ["60s"],
                "timeout": ["20s"],
            },
        )
        self.assertEqual(
            result["result"],
            {
                "series_count": 1,
                "truncated": True,
                "series": [{"metric_name": "run.googleapis.com/request_count", "point_count": 1}],
            },
        )

    @patch.object(observer, "observer_token", return_value="impersonated-token")
    @patch.object(
        observer,
        "fetch_json",
        return_value={
            "name": "locations/global/metricsScopes/123",
            "monitoredProjects": [
                {"name": "locations/global/metricsScopes/123/projects/123", "isTombstoned": False},
                {"name": "locations/global/metricsScopes/123/projects/456", "isTombstoned": False},
            ],
        },
    )
    def test_monitoring_queries_reject_cross_project_metrics_scope(
        self, _: object, __: object
    ) -> None:
        with self.assertRaisesRegex(observer.ObserverError, "single-project"):
            observer.observe("list_timeseries", VALID | {"filter": 'metric.type="example"'})

    def test_summaries_safely_normalize_null_nested_api_fields(self) -> None:
        self.assertEqual(
            observer.summary("list_log_entries", {"entries": [{"resource": None}]}, 10),
            {
                "entry_count": 1,
                "entries": [
                    {
                        "timestamp": None,
                        "severity": None,
                        "log_name": None,
                        "resource_type": None,
                    }
                ],
            },
        )
        self.assertEqual(
            observer.summary(
                "list_timeseries", {"timeSeries": [{"metric": None, "points": None}]}, 10
            ),
            {"series_count": 1, "series": [{"metric_type": None, "point_count": 0}]},
        )

    def test_launcher_ignores_hostile_python_environment(self) -> None:
        launcher = SCRIPT.with_name("gcp-observer-mcp-launcher")
        with tempfile.TemporaryDirectory() as temporary_directory:
            marker = Path(temporary_directory) / "sitecustomize-loaded"
            sitecustomize = Path(temporary_directory) / "sitecustomize.py"
            sitecustomize.write_text(f"from pathlib import Path\nPath({str(marker)!r}).touch()\n")
            environment = {
                "MATRIXEDMIND_GCP_OPERATOR_EMAIL": "operator@example.test",
                "PYTHONPATH": temporary_directory,
                "MATRIXEDMIND_TEST_SECRET": "must-not-reach-hostile-python",
            }
            result = subprocess.run(
                ["/bin/sh", str(launcher)],
                input="",
                text=True,
                capture_output=True,
                env=environment,
                cwd=SCRIPT.parents[2],
                timeout=10,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertFalse(marker.exists())

    @patch.object(
        observer.urllib.request.OpenerDirector,
        "open",
        side_effect=urllib.error.HTTPError(
            "https://run.googleapis.com/v2/example", 403, "forbidden", {}, None
        ),
    )
    def test_http_failure_reports_only_status_and_host(self, _: object) -> None:
        with self.assertRaisesRegex(
            observer.ObserverError, r"run\.googleapis\.com failed with HTTP 403"
        ):
            observer.fetch_json("https://run.googleapis.com/v2/example", "secret-token")


if __name__ == "__main__":
    unittest.main()
