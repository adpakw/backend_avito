import datetime
import logging
import sys
from typing import Any, Dict

import numpy as np

from app.clients.kafka import kafka_producer
from app.errors import (
    AdvertisementNotFoundError,
    ErrorInPrediction,
    ModelIsNotAvailable,
    ModerationTaskNotFoundError,
)
from app.repositories.advertisements import AdvertisementRepository
from app.repositories.moderation import ModerationRepository
from app.models.moderation import ModerationResult

logging.basicConfig(
    level=logging.INFO,
    format="\033[92m%(levelname)s\033[0m:  \t  %(message)s",
    stream=sys.stdout,
)

logger = logging.getLogger("app")


class ModerationService:
    _instance = None

    def __init__(self):
        self.ad_repo = AdvertisementRepository()
        self.moder_repo = ModerationRepository()

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    async def async_predict(self, item_id: int) -> int:
        try:

            logger.info(
                "Request to async predict: {item_id=%s}",
                item_id,
            )

            ad_data = await self.ad_repo.get(item_id)

            timestamp_now = datetime.datetime.now()

            moderation_task = await self.moder_repo.create(
                item_id, "pending", timestamp_now
            )

            await kafka_producer.send_moderation_request(
                moderation_task.id, item_id, timestamp_now
            )

            return moderation_task.id
        except AdvertisementNotFoundError as e:
            raise ErrorInPrediction("Advertisement Not Found In DB.")
        except Exception as e:
            raise ErrorInPrediction("Error in async prediction in MLService.")

    async def get_moderation_result(self, task_id: int) -> ModerationResult:
        try:

            logger.info(
                "Request for moderation result: {task_id=%s}",
                task_id,
            )

            moderation_task = await self.moder_repo.get(task_id)

            return ModerationResult(
                task_id=moderation_task.id,
                status=moderation_task.status,
                is_violation=moderation_task.is_violation,
                probability=moderation_task.probability,
            )
        except ModerationTaskNotFoundError as e:
            raise ModerationTaskNotFoundError("Moderation Task Not Found In DB.")
        except Exception as e:
            raise ErrorInPrediction("Error in async prediction in MLService.")

    async def complete_moderation_task(self, task_id: int, prediction_res: dict):
        await self.moder_repo.update(
            task_id,
            status="completed",
            is_violation=prediction_res["is_violation"],
            probability=prediction_res["probability"],
            processed_at=datetime.datetime.now(),
        )

    async def fail_moderation_task(self, task_id: int, error_message:str):
        await self.moder_repo.update(
            task_id,
            status="failed",
            error_message=error_message,
            processed_at=datetime.datetime.now(),
        )

    def get_moder_service(self):
        return self


moder_service_client = ModerationService()


def get_moder_service():
    return moder_service_client.get_moder_service()
