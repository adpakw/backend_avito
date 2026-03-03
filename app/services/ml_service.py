import logging
import sys
from typing import Any, Dict

import numpy as np

from app.errors import (
    AdvertisementNotFoundError,
    ErrorInPrediction,
    ModelIsNotAvailable,
)
from app.models.advertisement import AdvertisementWithSeller
from app.repositories.advertisements import AdvertisementRepository
from app.repositories.cache import CacheRepository
from app.repositories.model import model_client

logging.basicConfig(
    level=logging.INFO,
    format="\033[92m%(levelname)s\033[0m:  \t  %(message)s",
    stream=sys.stdout,
)

logger = logging.getLogger("app")


class MLService:
    _instance = None

    def __init__(self):
        self.model_client = model_client
        self.cache_repo = CacheRepository()

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def _prepare_features(self, ad_data: AdvertisementWithSeller) -> np.ndarray:
        is_verified = int(ad_data.is_verified_seller)

        images_normalized = min(ad_data.images_qty / 10, 1)

        description_length_normalized = min(len(ad_data.description) / 1000, 1)

        category_normalized = min(ad_data.category / 100, 1)

        return np.array(
            [
                [
                    is_verified,
                    images_normalized,
                    description_length_normalized,
                    category_normalized,
                ]
            ]
        )

    def predict(self, ad_data: AdvertisementWithSeller) -> Dict[str, Any]:
        try:
            logger.info(
                "Request to predict: {seller_id=%s, item_id=%s, "
                "is_verified_seller=%s, images_qty=%s, description=%s, category=%s}",
                ad_data.seller_id,
                ad_data.item_id,
                ad_data.is_verified_seller,
                ad_data.images_qty,
                ad_data.description,
                ad_data.category,
            )

            features = self._prepare_features(ad_data)

            is_violation, probability = self.model_client.predict(features)

            logger.info(
                "Result of prediction: {seller_id=%s, item_id=%s} - "
                "is_violation=%s, probability=%.4f",
                ad_data.seller_id,
                ad_data.item_id,
                is_violation,
                probability,
            )

            return {"is_violation": is_violation, "probability": probability}

        except ModelIsNotAvailable as e:
            raise ModelIsNotAvailable("Model is not available in MLService.")
        except Exception as e:
            raise ErrorInPrediction("Error in prediction in MLService.")

    async def simple_predict(self, item_id: int) -> Dict[str, Any]:
        try:
            cached_result = await self.cache_repo.get_prediction(item_id)
            if cached_result:
                logger.info(f"Returning cached prediction for item_id={item_id}")
                return cached_result

            logger.info(f"Cache miss, fetching from DB for item_id={item_id}")
            ad_repo = AdvertisementRepository()
            ad_data = await ad_repo.get(item_id)

            if ad_data.is_closed:
                raise AdvertisementNotFoundError(f"Advertisement {item_id} is closed")

            prediction = self.predict(ad_data)

            await self.cache_repo.set_prediction(item_id, prediction)

            return prediction

        except ModelIsNotAvailable as e:
            raise ModelIsNotAvailable("Model is not available in MLService.")
        except AdvertisementNotFoundError as e:
            raise ErrorInPrediction(str(e))
        except Exception as e:
            raise ErrorInPrediction(f"Error in prediction in MLService: {str(e)}")

    async def invalidate_cache(self, item_id: int) -> None:
        await self.cache_repo.delete_prediction(item_id)
        logger.info(f"Invalidated cache for item_id={item_id}")

    def get_ml_service(self):
        return self


ml_service_client = MLService()


def get_ml_service():
    return ml_service_client.get_ml_service()
