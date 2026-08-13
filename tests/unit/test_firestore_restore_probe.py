import subprocess
from unittest.mock import MagicMock, Mock

import pytest
from pymongo.errors import (
    ConfigurationError,
    ConnectionFailure,
    NetworkTimeout,
    OperationFailure,
    PyMongoError,
    ServerSelectionTimeoutError,
)

from scripts import firestore_restore_probe as probe

REQUIRED_QUERY = (
    "loadBalanced=true&tls=true&retryWrites=false&authMechanism=MONGODB-OIDC&"
    "authMechanismProperties=ENVIRONMENT:gcp,TOKEN_RESOURCE:FIRESTORE"
)
SOURCE_URI = f"mongodb://source.us-west1.firestore.goog:443/matrixedmind-spike?{REQUIRED_QUERY}"
TARGET_DB = "matrixedmind-dev-restore-validation-20260812-1030"
TARGET_URI = f"mongodb://target.us-west1.firestore.goog:443/{TARGET_DB}?{REQUIRED_QUERY}"
MARKER_ID = "restore-check-20260812"


@pytest.fixture
def fake_client() -> MagicMock:
    client = MagicMock()
    database = MagicMock()
    collection = Mock()
    client.__getitem__.return_value = database
    database.__getitem__.return_value = collection
    return client


def test_rejects_malformed_marker_before_connecting(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(probe.FIRESTORE_MONGO_URI_ENV, SOURCE_URI)
    factory = Mock()

    with pytest.raises(probe.ProbeValidationError, match="marker ID"):
        probe.run_restore_probe("seed", "bad/marker", client_factory=factory)

    factory.assert_not_called()


def test_rejects_missing_uri(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(probe.FIRESTORE_MONGO_URI_ENV, raising=False)

    with pytest.raises(probe.ProbeValidationError, match="FIRESTORE_MONGO_URI"):
        probe.run_restore_probe("seed", MARKER_ID)


@pytest.mark.parametrize(
    ("mode", "uri", "message"),
    [
        ("remove-everything", SOURCE_URI, "mode must be"),
        ("seed", "https://example.invalid/not-mongo", "FIRESTORE_MONGO_URI is invalid"),
        (
            "seed",
            f"mongodb://attacker.example:443/matrixedmind-spike?{REQUIRED_QUERY}",
            "FIRESTORE_MONGO_URI is invalid",
        ),
        (
            "seed",
            "mongodb://source.us-west1.firestore.goog:443/matrixedmind-spike?tls=true",
            "FIRESTORE_MONGO_URI is invalid",
        ),
        (
            "seed",
            f"mongodb://prod.us-west1.firestore.goog:443/matrixedmind-prod?{REQUIRED_QUERY}",
            "exact development source",
        ),
        (
            "verify-and-test",
            SOURCE_URI,
            "isolated restore target",
        ),
    ],
)
def test_rejects_invalid_mode_or_uri(
    monkeypatch: pytest.MonkeyPatch, mode: str, uri: str, message: str
) -> None:
    monkeypatch.setenv(probe.FIRESTORE_MONGO_URI_ENV, uri)

    with pytest.raises(probe.ProbeValidationError, match=message):
        probe.run_restore_probe(mode, MARKER_ID)


def test_seed_replaces_the_exact_marker_idempotently(
    monkeypatch: pytest.MonkeyPatch, fake_client: MagicMock
) -> None:
    monkeypatch.setenv(probe.FIRESTORE_MONGO_URI_ENV, SOURCE_URI)
    collection = fake_client["matrixedmind-spike"][probe.COLLECTION_NAME]

    assert probe.run_restore_probe("seed", MARKER_ID, client_factory=lambda _: fake_client) == 0
    assert probe.run_restore_probe("seed", MARKER_ID, client_factory=lambda _: fake_client) == 0

    assert collection.replace_one.call_count == 2
    collection.replace_one.assert_called_with(
        {"_id": MARKER_ID}, probe.marker_payload(MARKER_ID), upsert=True
    )
    fake_client.close.assert_called()


@pytest.mark.parametrize("document", [None, {"_id": MARKER_ID, "purpose": "wrong", "version": 1}])
def test_verify_rejects_missing_or_mismatched_marker(
    monkeypatch: pytest.MonkeyPatch, fake_client: MagicMock, document: object
) -> None:
    monkeypatch.setenv(probe.FIRESTORE_MONGO_URI_ENV, TARGET_URI)
    collection = fake_client[TARGET_DB][probe.COLLECTION_NAME]
    collection.find_one.return_value = document
    pytest_runner = Mock(return_value=0)

    with pytest.raises(probe.ProbeValidationError, match="missing or does not match"):
        probe.run_restore_probe(
            "verify-and-test",
            MARKER_ID,
            client_factory=lambda _: fake_client,
            pytest_runner=pytest_runner,
        )

    fake_client.admin.command.assert_not_called()
    pytest_runner.assert_not_called()


def test_cleanup_deletes_only_the_exact_marker(
    monkeypatch: pytest.MonkeyPatch, fake_client: MagicMock
) -> None:
    monkeypatch.setenv(probe.FIRESTORE_MONGO_URI_ENV, SOURCE_URI)
    collection = fake_client["matrixedmind-spike"][probe.COLLECTION_NAME]
    collection.delete_one.return_value.deleted_count = 1

    assert probe.run_restore_probe("cleanup", MARKER_ID, client_factory=lambda _: fake_client) == 0

    collection.delete_one.assert_called_once_with({"_id": MARKER_ID})
    collection.delete_many.assert_not_called()


def test_verify_pings_and_classifies_pytest_failure(
    monkeypatch: pytest.MonkeyPatch, fake_client: MagicMock
) -> None:
    monkeypatch.setenv(probe.FIRESTORE_MONGO_URI_ENV, TARGET_URI)
    collection = fake_client[TARGET_DB][probe.COLLECTION_NAME]
    collection.find_one.return_value = probe.marker_payload(MARKER_ID)
    pytest_runner = Mock(return_value=7)

    with pytest.raises(probe.ProbeRuntimeError) as error:
        probe.run_restore_probe(
            "verify-and-test",
            MARKER_ID,
            client_factory=lambda _: fake_client,
            pytest_runner=pytest_runner,
        )

    assert str(error.value) == "repository-contract/test-failure"

    fake_client.admin.command.assert_called_once_with("ping")
    pytest_runner.assert_called_once_with()


def test_firestore_test_child_output_is_discarded(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    sensitive_output = (
        "mongodb://sensitive.example token=secret credential=password response={'private': true}"
    )

    def fake_run(*args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
        assert kwargs["stdout"] is subprocess.DEVNULL
        assert kwargs["stderr"] is subprocess.DEVNULL
        return subprocess.CompletedProcess(
            args=args, returncode=7, stdout=sensitive_output, stderr=sensitive_output
        )

    monkeypatch.setattr(probe.subprocess, "run", fake_run)

    assert probe.run_firestore_tests() == 7
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == ""


@pytest.mark.parametrize(
    ("error", "category"),
    [
        (ServerSelectionTimeoutError("sensitive endpoint"), "server-selection-timeout"),
        (NetworkTimeout("sensitive endpoint"), "network-timeout"),
        (ConfigurationError("sensitive configuration"), "configuration-error"),
        (OperationFailure("sensitive token", code=18), "authorization-failure"),
        (OperationFailure("sensitive response", code=123), "operation-failure"),
        (ConnectionFailure("sensitive endpoint"), "connection-failure"),
        (PyMongoError("sensitive driver detail"), "driver-error"),
        (RuntimeError("sensitive unexpected detail"), "unexpected-error"),
    ],
)
def test_database_error_classification_ignores_sensitive_messages(
    error: Exception, category: str
) -> None:
    assert probe.classify_database_error(error) == category


def test_marker_read_failure_reports_only_stage_and_category(
    monkeypatch: pytest.MonkeyPatch, fake_client: MagicMock
) -> None:
    monkeypatch.setenv(probe.FIRESTORE_MONGO_URI_ENV, TARGET_URI)
    collection = fake_client[TARGET_DB][probe.COLLECTION_NAME]
    collection.find_one.side_effect = OperationFailure(
        "mongodb://sensitive.example token=do-not-log", code=18
    )

    with pytest.raises(probe.ProbeRuntimeError) as error:
        probe.run_restore_probe("verify-and-test", MARKER_ID, client_factory=lambda _: fake_client)

    assert str(error.value) == "marker-read/authorization-failure"
    assert "sensitive" not in str(error.value)
    assert "token" not in str(error.value)


def test_main_prints_only_sanitized_runtime_failure(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(
        probe,
        "run_restore_probe",
        Mock(side_effect=probe.ProbeRuntimeError("database-ping", "connection-failure")),
    )

    assert probe.main(["verify-and-test", "--marker-id", MARKER_ID]) == 1

    assert capsys.readouterr().err == ("restore probe failed: database-ping/connection-failure\n")


def test_main_never_prints_unexpected_exception_details(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(
        probe,
        "run_restore_probe",
        Mock(side_effect=RuntimeError("mongodb://sensitive.example token=do-not-log")),
    )

    assert probe.main(["verify-and-test", "--marker-id", MARKER_ID]) == 1

    captured = capsys.readouterr()
    assert captured.err == "restore probe failed: unexpected-error\n"
    assert "sensitive" not in captured.err
    assert "token" not in captured.err


def test_close_failure_is_classified_when_it_is_the_only_failure(
    monkeypatch: pytest.MonkeyPatch, fake_client: MagicMock
) -> None:
    monkeypatch.setenv(probe.FIRESTORE_MONGO_URI_ENV, TARGET_URI)
    collection = fake_client[TARGET_DB][probe.COLLECTION_NAME]
    collection.find_one.return_value = probe.marker_payload(MARKER_ID)
    fake_client.close.side_effect = ConnectionFailure("sensitive endpoint")

    with pytest.raises(probe.ProbeRuntimeError) as error:
        probe.run_restore_probe(
            "verify-and-test",
            MARKER_ID,
            client_factory=lambda _: fake_client,
            pytest_runner=Mock(return_value=0),
        )

    assert str(error.value) == "client-close/connection-failure"


def test_close_failure_does_not_mask_primary_database_failure(
    monkeypatch: pytest.MonkeyPatch, fake_client: MagicMock
) -> None:
    monkeypatch.setenv(probe.FIRESTORE_MONGO_URI_ENV, TARGET_URI)
    collection = fake_client[TARGET_DB][probe.COLLECTION_NAME]
    collection.find_one.side_effect = OperationFailure("sensitive token", code=18)
    fake_client.close.side_effect = ConnectionFailure("different sensitive endpoint")

    with pytest.raises(probe.ProbeRuntimeError) as error:
        probe.run_restore_probe("verify-and-test", MARKER_ID, client_factory=lambda _: fake_client)

    assert str(error.value) == "marker-read/authorization-failure"
