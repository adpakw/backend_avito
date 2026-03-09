import logging
import sys

from fastapi import APIRouter, Depends, HTTPException, status

from app.dependencies.auth import get_current_active_account
from app.errors import AdvertisementNotFoundError
from app.models.account import Account
from app.models.advertisement import Advertisement, AdvertisementID
from app.services.close_service import CloseService, get_close_service

logging.basicConfig(
    level=logging.INFO,
    format="\033[92m%(levelname)s\033[0m:  \t  %(message)s",
    stream=sys.stdout,
)

logger = logging.getLogger("app")
router = APIRouter(dependencies=[Depends(get_current_active_account)])


@router.post("/close", response_model=Advertisement)
async def close_advertisement_endpoint(
    request: AdvertisementID,
    close_service: CloseService = Depends(get_close_service),
    current_account: Account = Depends(get_current_active_account),
):
    logger.info(
        f"User {current_account.login} requested to close advertisement {request.id}"
    )
    try:
        closed_ad = await close_service.close_advertisement(request.id)
        return closed_ad
    except AdvertisementNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Advertisement with id {request.id} not found",
        )
    except Exception as e:
        logger.error(f"Error closing advertisement {request.id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error closing advertisement",
        )
