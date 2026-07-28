from pytest import MonkeyPatch

from tests.firestore.conftest import FIRESTORE_MONGO_URI_ENV, _validated_firestore_uri


def test_firestore_uri_accepts_gcp_oidc(monkeypatch: MonkeyPatch) -> None:
    uri = (
        "mongodb://uid.nam5.firestore.goog:443/matrixedmind-spike?"
        "loadBalanced=true&tls=true&retryWrites=false&authMechanism=MONGODB-OIDC&"
        "authMechanismProperties=ENVIRONMENT:gcp,TOKEN_RESOURCE:FIRESTORE"
    )
    monkeypatch.setenv(FIRESTORE_MONGO_URI_ENV, uri)

    assert _validated_firestore_uri() == uri


def test_firestore_uri_accepts_scram(monkeypatch: MonkeyPatch) -> None:
    uri = (
        "mongodb://user:password@uid.nam5.firestore.goog:443/matrixedmind-spike?"
        "loadBalanced=true&authMechanism=SCRAM-SHA-256&tls=true&retryWrites=false"
    )
    monkeypatch.setenv(FIRESTORE_MONGO_URI_ENV, uri)

    assert _validated_firestore_uri() == uri
