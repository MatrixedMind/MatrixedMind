# Firestore MongoDB Compatibility Spike

## Status

The opt-in compatibility suite is implemented. Local MongoDB verification can run without GCP
credentials. Firestore verification remains pending until a dedicated Firestore Enterprise database
and SCRAM credential are supplied through `FIRESTORE_MONGO_URI`.

The suite is intentionally destructive to the `records` collection in the database named by that
URI. Use a dedicated non-production spike database only.

## Provision the spike database

Prerequisites:

- A GCP project with billing enabled.
- `Owner` or `Datastore Owner` access to create the database.
- `User Creds Admin` access to create a SCRAM credential.
- A dedicated database ID and location selected for this spike.

Create an Enterprise database with MongoDB-compatible data access:

```bash
gcloud firestore databases create \
  --database=matrixedmind-spike \
  --location=LOCATION \
  --edition=enterprise \
  --enable-mongodb-compatible-data-access \
  --delete-protection
```

Retrieve the database UID and location:

```bash
gcloud firestore databases describe \
  --database=matrixedmind-spike \
  --format='yaml(locationId,uid)'
```

Create a dedicated SCRAM user. The generated password is displayed once; store it in a secure
password manager and never commit or paste it into project files, logs, or issue comments.

```bash
gcloud firestore user-creds create matrixedmind-spike \
  --database=matrixedmind-spike
```

Grant that database user read/write access to the dedicated database. The repository constructor
also creates two indexes, so the spike identity needs `roles/datastore.indexAdmin` in addition to
`roles/datastore.user`, or an administrator must create both indexes before the run. Prefer a
database-scoped IAM condition for both grants.

The required indexes are:

```text
records: space ASC, slug ASC, unique
records: space ASC, parent_id ASC
```

Google's current index API accepts one index per create request. MatrixedMind already calls
`create_index` once for each index, so no batching change is expected.

## Connection settings

Construct the SCRAM URI using the database UID, location, database ID, and URL-encoded username and
password:

```text
mongodb://USERNAME:PASSWORD@UID.LOCATION.firestore.goog:443/matrixedmind-spike?loadBalanced=true&authMechanism=SCRAM-SHA-256&tls=true&retryWrites=false
```

All four query options are required:

- `loadBalanced=true` prevents topology discovery against the compatibility endpoint.
- `authMechanism=SCRAM-SHA-256` selects the provisioned database credential.
- `tls=true` encrypts the connection.
- `retryWrites=false` disables retryable writes, which Firestore compatibility does not support.

Keep local development on `MONGO_URI`. Use `FIRESTORE_MONGO_URI` only for the opt-in spike command so
the normal test suite never needs cloud credentials and local Docker MongoDB is never replaced.

## Run the spike

Start local MongoDB and establish the local baseline first:

```bash
docker compose up -d mongo
uv run pytest tests/integration/test_mongo_connection.py tests/integration/test_mongo_repository.py
```

Then inject the Firestore URI through the shell or a secret-aware runner and run only the opt-in
suite:

```bash
FIRESTORE_MONGO_URI='<secret-uri>' uv run pytest tests/firestore -rs
```

Do not add `FIRESTORE_MONGO_URI` to `.env`, `.env.example`, CI variables, or command transcripts.
The test harness rejects non-Firestore hosts and URIs missing the required connection options before
it deletes test data.

The suite verifies:

- The reusable repository contract.
- Compound uniqueness for `(space, slug)` and adapter-level duplicate error mapping.
- PyMongo-generated and round-tripped BSON `ObjectId` values.
- Repository updates implemented with `update_one` and `$set`, including revision creation.
- Stable `created_at`, then `_id`, sorting for child lists.
- A direct database ping and the application `MongoConnection.ping` readiness path.

## Adapter findings

No MatrixedMind adapter change is currently required by the documented Firestore feature set:
compound and unique indexes, `ObjectId`, `$set`, sorting, `createIndex`, and ping are documented as
supported. This is a documentation-derived expectation, not a successful runtime result. Record the
exact PyMongo exception and operation here if the opt-in suite proves otherwise.

The existing `MongoRecordRepository` creates one index per request, which matches Firestore's
current index-management limitation. Firestore does not create an `_id` index automatically, but it
does enforce `_id` uniqueness; the repository only depends on identity lookup and uniqueness.

## Result record

As of 2026-07-27:

- Local MongoDB: repository connection and contract coverage passed as part of the full test suite;
  `119 passed, 6 skipped`.
- Firestore MongoDB compatibility: blocked pending a dedicated database and SCRAM URI.
- Exact external blocker: `FIRESTORE_MONGO_URI` and its backing Firestore Enterprise spike database
  have not been provisioned in this workspace.

Credential-free quality results on this branch:

```text
uv run ruff format --check .    passed
uv run ruff check .             passed
uv run mypy app                 passed
uv run pytest -rs               119 passed, 6 skipped
uv run pre-commit run --all-files passed
```

After an external run, replace this section with the date, database region, PyMongo version, exact
commands, pass/fail totals, and any sanitized error output. Never record the host UID or credential.

## MongoDB Atlas fallback criteria

Choose MongoDB Atlas only if at least one of these remains true after reproducing the result on a
fresh dedicated Firestore spike database:

- A required repository-contract behavior is unsupported or observably incorrect.
- `ObjectId`, duplicate-key translation, `$set`, deterministic sorting, or readiness cannot be made
  reliable without a Firestore-specific repository fork.
- Required compound/unique indexes cannot be created and operated with a least-privilege deployment
  model.
- A documented Firestore limitation blocks the secure Cloud MVP and has no acceptable short-term
  workaround.
- Measured latency, availability, or cost for the MatrixedMind access pattern fails an explicitly
  recorded MVP acceptance threshold.

Do not fall back for a transient credential, IAM, DNS, or local tooling error. Record and fix those
as setup blockers, then rerun the same suite.

## References

- [Create and manage Firestore MongoDB-compatible databases](https://docs.cloud.google.com/firestore/mongodb-compatibility/docs/create-databases)
- [Authenticate and connect](https://docs.cloud.google.com/firestore/mongodb-compatibility/docs/connect)
- [Manage indexes](https://docs.cloud.google.com/firestore/mongodb-compatibility/docs/indexing)
- [Supported MongoDB 6.0 features](https://docs.cloud.google.com/firestore/mongodb-compatibility/docs/supported-features-60)
- [Behavior differences](https://docs.cloud.google.com/firestore/mongodb-compatibility/docs/behavior-differences)
