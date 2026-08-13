from __future__ import annotations

import argparse
from collections.abc import Sequence

from app.adapters.mongo.auth import MongoOwnerAuthRepository
from app.adapters.mongo.connection import MongoConnection
from app.auth.service import issue_operator_credential
from app.settings import settings


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Issue a one-time MatrixedMind owner credential")
    parser.add_argument("purpose", choices=("bootstrap", "recovery"))
    args = parser.parse_args(argv)
    repo = MongoOwnerAuthRepository(
        MongoConnection.get_db(), ensure_indexes=settings.mongo_ensure_indexes
    )
    try:
        credential = issue_operator_credential(repo, args.purpose, settings)
    except ValueError as exc:
        parser.error(str(exc))
    print(credential)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
