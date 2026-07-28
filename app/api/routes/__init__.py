from fastapi import APIRouter

from app.api.routes.llm import router as llm_router
from app.api.routes.records import router as records_router

router = APIRouter()
router.include_router(records_router)
router.include_router(llm_router)


@router.get("/status")
async def status() -> dict[str, str]:
    return {"status": "api is up"}
