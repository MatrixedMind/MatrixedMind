from unittest.mock import MagicMock, Mock

import pytest

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


def test_verify_pings_and_propagates_pytest_failure(
    monkeypatch: pytest.MonkeyPatch, fake_client: MagicMock
) -> None:
    monkeypatch.setenv(probe.FIRESTORE_MONGO_URI_ENV, TARGET_URI)
    collection = fake_client[TARGET_DB][probe.COLLECTION_NAME]
    collection.find_one.return_value = probe.marker_payload(MARKER_ID)
    pytest_runner = Mock(return_value=7)

    assert (
        probe.run_restore_probe(
            "verify-and-test",
            MARKER_ID,
            client_factory=lambda _: fake_client,
            pytest_runner=pytest_runner,
        )
        == 7
    )

    fake_client.admin.command.assert_called_once_with("ping")
    pytest_runner.assert_called_once_with()
