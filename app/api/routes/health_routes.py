from fastapi import APIRouter
from pydantic import BaseModel


router = APIRouter(tags=["health"])


class HealthResponse(BaseModel):
    status: str


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """
    Return service health status.

    Returns:
        HealthResponse with status set to "ok".
    """
    return HealthResponse(status="ok")

