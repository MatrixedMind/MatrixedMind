FROM python:3.12-slim

ARG SOURCE_REVISION=local

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    SOURCE_REVISION=${SOURCE_REVISION}

WORKDIR /app

COPY pyproject.toml uv.lock README.md ./
COPY --from=ghcr.io/astral-sh/uv:0.5.20 /uv /usr/local/bin/uv

RUN uv sync --frozen --no-dev

COPY app ./app

EXPOSE 8080
CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
