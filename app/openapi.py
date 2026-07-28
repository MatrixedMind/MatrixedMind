from typing import Any

from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi
from fastapi.routing import APIRoute

LLM_API_PREFIX = "/api/llm/"


def build_llm_openapi_schema(app: FastAPI, server_url: str) -> dict[str, Any]:
    """Build the deliberately narrow schema imported by the ChatGPT Action."""
    llm_routes = [
        route
        for route in app.routes
        if isinstance(route, APIRoute) and route.path.startswith(LLM_API_PREFIX)
    ]
    schema = get_openapi(
        title="MatrixedMind LLM API",
        version="1.0.0",
        description=(
            "A narrow, non-destructive API for reading and upserting private draft "
            "MatrixedMind records in token-authorized spaces."
        ),
        routes=llm_routes,
        servers=[{"url": server_url.rstrip("/")}],
    )
    components = schema.setdefault("components", {})
    components["securitySchemes"] = {
        "LlmBearerToken": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "API key",
            "description": "Scoped MatrixedMind LLM token.",
        }
    }
    for path_item in schema["paths"].values():
        for operation in path_item.values():
            operation["security"] = [{"LlmBearerToken": []}]
    return schema
