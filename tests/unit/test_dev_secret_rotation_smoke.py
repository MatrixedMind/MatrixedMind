from unittest.mock import MagicMock, Mock, patch

import pytest

from scripts import dev_secret_rotation_smoke as smoke

REQUIRED_QUERY = (
    "loadBalanced=true&tls=true&retryWrites=false&authMechanism=MONGODB-OIDC&"
    "authMechanismProperties=ENVIRONMENT:gcp,TOKEN_RESOURCE:FIRESTORE"
)
VALID_URI = f"mongodb://uid.us-west1.firestore.goog:443/matrixedmind-spike?{REQUIRED_QUERY}"
VALID_SERVICE_URL = "https://matrixedmind-dev-123456789.us-west1.run.app"
RUN_ID = "closeout-20260812"
UNIQUE_SUFFIX = "0123456789abcdef"
TOKEN_ID = f"closeout-smoke-{RUN_ID}-{UNIQUE_SUFFIX}"


class FakeResponse:
    def __init__(self, status_code: int, text: str = "") -> None:
        self.status_code = status_code
        self.text = text


@pytest.fixture
def fake_mongo_client() -> MagicMock:
    client = MagicMock()
    database = MagicMock()
    database.personal_access_tokens.find_one.return_value = None
    client.__getitem__.return_value = database
    return client


@pytest.fixture
def fake_http_client() -> Mock:
    return Mock()


def configure_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(smoke.FIRESTORE_MONGO_URI_ENV, VALID_URI)
    monkeypatch.setenv(smoke.DEV_SERVICE_URL_ENV, VALID_SERVICE_URL)


@pytest.mark.parametrize(
    ("run_id", "uri", "service_url"),
    [
        ("bad/run", VALID_URI, VALID_SERVICE_URL),
        (RUN_ID, "https://example.invalid/not-mongo", VALID_SERVICE_URL),
        (
            RUN_ID,
            f"mongodb://attacker.example:443/matrixedmind-spike?{REQUIRED_QUERY}",
            VALID_SERVICE_URL,
        ),
        (
            RUN_ID,
            "mongodb://uid.us-west1.firestore.goog:443/matrixedmind-spike?tls=true",
            VALID_SERVICE_URL,
        ),
        (
            RUN_ID,
            f"mongodb://uid.us-west1.firestore.goog:443/matrixedmind-prod?{REQUIRED_QUERY}",
            VALID_SERVICE_URL,
        ),
        (RUN_ID, VALID_URI, "http://example.run.app"),
        (RUN_ID, VALID_URI, "https://other-service-123456789.us-west1.run.app"),
    ],
)
def test_rejects_malformed_inputs_before_connecting(
    monkeypatch: pytest.MonkeyPatch, run_id: str, uri: str, service_url: str
) -> None:
    monkeypatch.setenv(smoke.FIRESTORE_MONGO_URI_ENV, uri)
    monkeypatch.setenv(smoke.DEV_SERVICE_URL_ENV, service_url)
    mongo_factory = Mock()

    with pytest.raises(smoke.SmokeValidationError):
        smoke.run_smoke(run_id, mongo_client_factory=mongo_factory)

    mongo_factory.assert_not_called()


def test_rejects_missing_required_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(smoke.FIRESTORE_MONGO_URI_ENV, raising=False)
    monkeypatch.delenv(smoke.DEV_SERVICE_URL_ENV, raising=False)

    with pytest.raises(smoke.SmokeValidationError):
        smoke.run_smoke(RUN_ID)


def test_metadata_request_uses_google_header_and_canonical_audience() -> None:
    http_client = Mock()
    http_client.get.return_value = FakeResponse(200, "identity-token")

    assert smoke.metadata_identity_token(http_client, VALID_SERVICE_URL) == "identity-token"

    http_client.get.assert_called_once_with(
        smoke.METADATA_IDENTITY_URL,
        params={"audience": VALID_SERVICE_URL},
        headers={"Metadata-Flavor": "Google"},
    )


def test_happy_path_uses_separate_pat_and_serverless_authorization_headers(
    monkeypatch: pytest.MonkeyPatch, fake_mongo_client: MagicMock, fake_http_client: Mock
) -> None:
    configure_env(monkeypatch)
    repository = Mock()
    fake_http_client.get.side_effect = [
        FakeResponse(200, "identity-token"),
        FakeResponse(200),
        FakeResponse(200),
        FakeResponse(200),
        FakeResponse(401),
    ]

    with patch.object(smoke, "MongoPersonalAccessTokenRepository", return_value=repository):
        assert (
            smoke.run_smoke(
                RUN_ID,
                mongo_client_factory=lambda _: fake_mongo_client,
                http_client_factory=lambda: fake_http_client,
                raw_token_factory=lambda: "raw-personal-access-token",
                unique_suffix_factory=lambda: UNIQUE_SUFFIX,
            )
            == 0
        )

    records_call = fake_http_client.get.call_args_list[3]
    platform_headers = {"X-Serverless-Authorization": "Bearer identity-token"}
    assert fake_http_client.get.call_args_list[1].kwargs == {"headers": platform_headers}
    assert fake_http_client.get.call_args_list[2].kwargs == {"headers": platform_headers}
    assert records_call.args == (f"{VALID_SERVICE_URL}/api/llm/records",)
    assert records_call.kwargs == {
        "params": {"space": smoke.SMOKE_SPACE},
        "headers": {
            "Authorization": "Bearer raw-personal-access-token",
            "X-Serverless-Authorization": "Bearer identity-token",
        },
    }
    assert repository.revoke.call_args_list == [
        ((TOKEN_ID,),),
        ((TOKEN_ID,),),
    ]


def test_non_200_check_revokes_saved_token_on_failure(
    monkeypatch: pytest.MonkeyPatch, fake_mongo_client: MagicMock, fake_http_client: Mock
) -> None:
    configure_env(monkeypatch)
    repository = Mock()
    fake_http_client.get.side_effect = [FakeResponse(200, "identity-token"), FakeResponse(503)]

    with (
        patch.object(smoke, "MongoPersonalAccessTokenRepository", return_value=repository),
        pytest.raises(smoke.SmokeCheckError, match="health"),
    ):
        smoke.run_smoke(
            RUN_ID,
            mongo_client_factory=lambda _: fake_mongo_client,
            http_client_factory=lambda: fake_http_client,
            unique_suffix_factory=lambda: UNIQUE_SUFFIX,
        )

    repository.revoke.assert_called_once_with(TOKEN_ID)
    fake_http_client.close.assert_called_once_with()
    fake_mongo_client.close.assert_called_once_with()


def test_save_failure_does_not_attempt_revocation(
    monkeypatch: pytest.MonkeyPatch, fake_mongo_client: MagicMock, fake_http_client: Mock
) -> None:
    configure_env(monkeypatch)
    repository = Mock()
    repository.save.side_effect = RuntimeError("save failed")

    with (
        patch.object(smoke, "MongoPersonalAccessTokenRepository", return_value=repository),
        pytest.raises(RuntimeError, match="save failed"),
    ):
        smoke.run_smoke(
            RUN_ID,
            mongo_client_factory=lambda _: fake_mongo_client,
            http_client_factory=lambda: fake_http_client,
            unique_suffix_factory=lambda: UNIQUE_SUFFIX,
        )

    repository.revoke.assert_not_called()


def test_generated_token_id_collision_fails_before_save(
    monkeypatch: pytest.MonkeyPatch, fake_mongo_client: MagicMock, fake_http_client: Mock
) -> None:
    configure_env(monkeypatch)
    repository = Mock()
    fake_mongo_client[smoke.SOURCE_DATABASE].personal_access_tokens.find_one.return_value = {
        "_id": TOKEN_ID
    }

    with (
        patch.object(smoke, "MongoPersonalAccessTokenRepository", return_value=repository),
        pytest.raises(smoke.SmokeValidationError, match="already exists"),
    ):
        smoke.run_smoke(
            RUN_ID,
            mongo_client_factory=lambda _: fake_mongo_client,
            http_client_factory=lambda: fake_http_client,
            unique_suffix_factory=lambda: UNIQUE_SUFFIX,
        )

    repository.save.assert_not_called()
    repository.revoke.assert_not_called()


def test_post_revocation_requires_401(
    monkeypatch: pytest.MonkeyPatch, fake_mongo_client: MagicMock, fake_http_client: Mock
) -> None:
    configure_env(monkeypatch)
    repository = Mock()
    fake_http_client.get.side_effect = [
        FakeResponse(200, "identity-token"),
        FakeResponse(200),
        FakeResponse(200),
        FakeResponse(200),
        FakeResponse(200),
    ]

    with (
        patch.object(smoke, "MongoPersonalAccessTokenRepository", return_value=repository),
        pytest.raises(smoke.SmokeCheckError, match="pat-rejected"),
    ):
        smoke.run_smoke(
            RUN_ID,
            mongo_client_factory=lambda _: fake_mongo_client,
            http_client_factory=lambda: fake_http_client,
            unique_suffix_factory=lambda: UNIQUE_SUFFIX,
        )

    assert repository.revoke.call_count == 2


def test_cleanup_failures_do_not_mask_primary_check_failure(
    monkeypatch: pytest.MonkeyPatch, fake_mongo_client: MagicMock, fake_http_client: Mock
) -> None:
    configure_env(monkeypatch)
    repository = Mock()
    repository.revoke.side_effect = RuntimeError("cleanup revoke failed")
    fake_http_client.get.side_effect = [FakeResponse(200, "identity-token"), FakeResponse(503)]
    fake_http_client.close.side_effect = RuntimeError("HTTP close failed")
    fake_mongo_client.close.side_effect = RuntimeError("Mongo close failed")

    with (
        patch.object(smoke, "MongoPersonalAccessTokenRepository", return_value=repository),
        pytest.raises(smoke.SmokeCheckError, match="health"),
    ):
        smoke.run_smoke(
            RUN_ID,
            mongo_client_factory=lambda _: fake_mongo_client,
            http_client_factory=lambda: fake_http_client,
            unique_suffix_factory=lambda: UNIQUE_SUFFIX,
        )

    repository.revoke.assert_called_once_with(TOKEN_ID)
    fake_http_client.close.assert_called_once_with()
    fake_mongo_client.close.assert_called_once_with()


def test_cleanup_failure_fails_an_otherwise_successful_run(
    monkeypatch: pytest.MonkeyPatch, fake_mongo_client: MagicMock, fake_http_client: Mock
) -> None:
    configure_env(monkeypatch)
    repository = Mock()
    fake_http_client.get.side_effect = [
        FakeResponse(200, "identity-token"),
        FakeResponse(200),
        FakeResponse(200),
        FakeResponse(200),
        FakeResponse(401),
    ]
    fake_http_client.close.side_effect = RuntimeError("HTTP close failed")

    with (
        patch.object(smoke, "MongoPersonalAccessTokenRepository", return_value=repository),
        pytest.raises(RuntimeError, match="HTTP close failed"),
    ):
        smoke.run_smoke(
            RUN_ID,
            mongo_client_factory=lambda _: fake_mongo_client,
            http_client_factory=lambda: fake_http_client,
            unique_suffix_factory=lambda: UNIQUE_SUFFIX,
        )

    fake_mongo_client.close.assert_called_once_with()
