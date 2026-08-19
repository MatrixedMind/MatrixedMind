from pathlib import Path


def test_compose_mongo_supports_authenticated_single_node_transactions() -> None:
    compose = Path("compose.yaml").read_text()

    assert '"--replSet", "rs0"' in compose
    assert '"--keyFile", "/etc/mongo-keyfile/keyfile"' in compose
    assert "mongo-keyfile-init:" in compose
    assert "mongo-replica-init:" in compose
    assert 'host: "mongo:27017"' in compose
    assert "mongo_keyfile:/etc/mongo-keyfile:ro" in compose
    assert '"127.0.0.1:27017:27017"' in compose


def test_compose_api_waits_for_replica_set_and_disables_retryable_writes() -> None:
    compose = Path("compose.yaml").read_text()

    assert "mongo-replica-init:\n        condition: service_completed_successfully" in compose
    assert "replicaSet=rs0&directConnection=true&retryWrites=false" in compose
