# MatrixedMind

MatrixedMind is a FastAPI app for storing and rendering structured markdown records.

## Happy Paths

### 1. Local Development
```bash
docker compose up --build
```
Access the app at http://localhost:8000.

### 2. Local Tests
```bash
uv run pytest
```

### 3. GCP Dev Deploy
```bash
cd infra/terraform/envs/dev
terraform init
terraform apply
```
