# MatrixedMind

MatrixedMind is an open-source infrastructure template for building your own personal or team-owned knowledge system.

It gives you a self-hosted Notes API that runs on Google Cloud Run and stores Markdown notes in Google Cloud Storage. Infra is fully provisioned with Terraform.

The core goals are:
- Composable – drop this service into any workflow or automation pipeline.
- Cloud-native – minimal, serverless deployment on GCP.
- Extensible – use it as the backend for AI/LLM assistants, personal agents, or chat-based note capture.
- Open – licensed under AGPL-3.0-or-later to guarantee it stays free and modifiable.

---

## Key Features

- FastAPI microservice with authenticated note creation and retrieval endpoints.
- Notes are saved as Markdown in a versioned GCS bucket.
- Automatic index maintenance: project / section / note hierarchy.
- Terraform that stands up:
  - Cloud Run service
  - Service account and IAM
  - GCS bucket for notes
  - Artifact Registry repo for your container image
  - Required Google APIs
- Simple shared-secret API key auth (X-Notes-Key header).
- MkDocs-friendly content layout so you can generate a browsable wiki.

---

## Architecture Overview

High level:

1. You send a POST request to the MatrixedMind API with:
   - project  
   - section  
   - title  
   - body  

2. The API writes (or appends) a Markdown file like:
   ```
   notes/<project>/<section>/<title>.md
   ```

3. The API maintains index files:
   ```
   notes/<project>/_index.md
   notes/<project>/<section>/_index.md
   ```

4. You or an automated job can build docs (MkDocs or similar) from those Markdown files and publish them, or just treat the bucket as your personal knowledge base.

This means:
- You control your data.
- You can point other tools (including an LLM assistant) at this API instead of pasting stuff all over SaaS notes apps.

---

## Quick Start

### 0. Prereqs

You’ll need:
- A Google Cloud project with billing enabled.  
- gcloud CLI installed and authenticated.  
- terraform installed.  
- docker installed (or you can use Cloud Build to build/push the container image).

### 1. Build and push the container

From the app/ directory:

```
PROJECT_ID="your-project-id"
REGION="us-west1"
REPO_NAME="matrixedmind-repo"
IMAGE_NAME="notes-api"
IMAGE_TAG="v1"

# Enable Artifact Registry in your project before running this if needed.
# (Terraform will also try to enable it.)

gcloud artifacts repositories create $REPO_NAME \
  --repository-format=docker \
  --location=$REGION \
  --description="MatrixedMind container repo" || true

# Build the image locally:
docker build -t $REGION-docker.pkg.dev/$PROJECT_ID/$REPO_NAME/$IMAGE_NAME:$IMAGE_TAG .

# Push the image:
docker push $REGION-docker.pkg.dev/$PROJECT_ID/$REPO_NAME/$IMAGE_NAME:$IMAGE_TAG
```

You’ll use that pushed image reference in Terraform as container_image.

### 2. Deploy infra with Terraform

From the terraform/ directory:

```
API_KEY=$(openssl rand -hex 32)

terraform init
terraform apply \
  -var="project_id=${PROJECT_ID}" \
  -var="region=${REGION}" \
  -var="bucket_name=matrixedmind-notes-${PROJECT_ID}" \
  -var="api_key=${API_KEY}" \
  -var="container_image=${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO_NAME}/${IMAGE_NAME}:${IMAGE_TAG}"
```

Terraform will:
- create / configure a notes bucket  
- create a service account  
- give it storage access  
- create a Cloud Run service  
- expose the service URL  
- wire in your API key and bucket name as environment variables  

Terraform will output the Cloud Run URL at the end.

### 3. Test the service

```
CLOUD_RUN_URL=$(terraform output -raw cloud_run_url)

# Health check (no authentication required)
curl "${CLOUD_RUN_URL}/ping"

# Add a note
curl -X POST \
  -H "Content-Type: application/json" \
  -H "X-Notes-Key: ${API_KEY}" \
  --data '{
    "project": "Personal Wiki",
    "section": "Ideas",
    "title": "Offline Sync Plan",
    "body": "Test adding new notes through MatrixedMind API.",
    "mode": "append"
  }' \
  "${CLOUD_RUN_URL}/api/v1/notes"

# Read the note back
curl -H "X-Notes-Key: ${API_KEY}" \
  "${CLOUD_RUN_URL}/api/v1/notes?project=Personal%20Wiki&section=Ideas&title=Offline%20Sync%20Plan"
```

At this point you’re live.

---

## Repo Layout

```
app/
  __init__.py
  main.py
  models.py
  storage.py
  requirements.txt
  Dockerfile
terraform/
  main.tf
  variables.tf
  outputs.tf
  versions.tf
LICENSE
USE_POLICY.md
README.md
```

---

## Security Model

- Cloud Run is publicly invokable by default in this template.  
- All meaningful endpoints require a header:  
  X-Notes-Key: <your-secret>

### Public Health Check Endpoint

The `/ping` endpoint is intentionally **public and unauthenticated** for the following reasons:
- External monitoring tools and load balancers can verify service availability without API credentials
- Cloud Run's built-in health checks can validate service status
- Operational teams can quickly verify deployment success

**Security considerations:**
- The endpoint returns only `{"status": "ok"}` with no sensitive information
- It does not expose service version, configuration, dependencies, or data
- It confirms the service exists and is responsive, which is acceptable for a health check
- All data access endpoints (`/api/v1/notes`, `/api/v1/index`) remain protected by API key authentication

### Key Protection

- Random people on the internet can hit /ping but can't write or read your notes without the secret.  
- You can rotate the secret by updating the Cloud Run service via Terraform (-var="api_key=..." again).  

If you want to lock it down further (private Cloud Run, VPC, etc.), that's possible, but kept out of v1 for simplicity.

---

## License

MatrixedMind is licensed under the GNU Affero General Public License v3.0 or later (AGPL-3.0-or-later).

AGPL means:
- You’re free to use, modify, and redistribute.  
- If you run a modified version as a service for others, you must also make your modified source available.  
- You cannot take this code, close it, and sell it as proprietary.

See LICENSE and USE_POLICY.md for details.

---

## Use Policy (Human-Friendly Summary)

Allowed:
- Personal use, self-hosting, lab environments.  
- Embedding MatrixedMind inside a bigger product or consulting engagement.  
- Running it as part of a managed service that adds real functionality on top, as long as you clearly say MatrixedMind is in the stack and you keep your modified MatrixedMind code open.

Not allowed:
- Repackaging MatrixedMind (or a trivial fork) as a closed, paid “MatrixedMind-as-a-Service.”  
- Rebranding it and pretending you wrote it.

---

## Status

Alpha / experimental. Expect breaking changes.
