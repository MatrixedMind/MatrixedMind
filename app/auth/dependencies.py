from typing import Any

from fastapi import HTTPException, status

from app.settings import settings


async def get_current_user() -> dict[str, Any]:
    if settings.app_env == "local":
        return {"id": "dev-user", "name": "Dev User"}

    # Placeholder for Identity Platform
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Identity Platform auth not implemented yet",
    )
