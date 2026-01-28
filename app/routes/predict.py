import logging
import sys

from fastapi import APIRouter, Depends, HTTPException, status

from app.errors import ErrorInPrediction, ModelIsNotAvailable
from app.model import get_model
from app.pydantic_models import Advertisement, PredictResponse
from app.services.ml_service import MLService, get_ml_service

logging.basicConfig(
    level=logging.INFO,
    format="\033[92m%(levelname)s\033[0m:  \t  %(message)s",
    stream=sys.stdout,
)

logger = logging.getLogger("app")
router = APIRouter(dependencies=[Depends(get_model), Depends(get_ml_service)])


@router.post("/predict", response_model=PredictResponse)
async def predict_endpoint(
    ad: Advertisement, ml_service_client: MLService = Depends(get_ml_service)
):
    try:
        prediction = ml_service_client.predict(ad)
    except ModelIsNotAvailable:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Model is not available.",
        )
    except ErrorInPrediction:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error in prediction.",
        )

    return PredictResponse(**prediction)
