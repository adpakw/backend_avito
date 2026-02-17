import logging
import sys

from fastapi import APIRouter, Depends, HTTPException, status

from app.errors import ErrorInPrediction, ModerationTaskNotFoundError
from app.models.moderation import ModerationResult
from app.services.moderation_service import ModerationService, get_moder_service

logging.basicConfig(
    level=logging.INFO,
    format="\033[92m%(levelname)s\033[0m:  \t  %(message)s",
    stream=sys.stdout,
)

logger = logging.getLogger("app")
router = APIRouter()


@router.get("/moderation_result/{task_id}", response_model=ModerationResult)
async def moderation_result_endpoint(
    task_id: int,
    moder_service_client: ModerationService = Depends(get_moder_service),
):
    try:
        moderation_result = await moder_service_client.get_moderation_result(task_id)
    except ErrorInPrediction:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error in prediction.",
        )
    except ModerationTaskNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No task with id = {task_id}",
        )

    return moderation_result
