# app/Dockerfile
FROM python:3.12-slim

# Install system deps (if any); google-cloud-storage is pure python so we're light
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# uvicorn entrypoint
ENV PYTHONUNBUFFERED=1

# Cloud Run will listen on $PORT
ENV PORT=8080

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
