import asyncio
import json
import logging
import sys
from typing import Optional

from aiokafka import ConsumerRecord

from app.clients.kafka import (
    KafkaConsumer,
    KafkaProducer,
    get_kafka_producer,
    get_kafka_consumer,
)
from app.services.ml_service import MLService, get_ml_service
from app.services.moderation_service import ModerationService, get_moder_service
from app.repositories.advertisements import AdvertisementRepository
from app.errors import (
    AdvertisementNotFoundError,
    ErrorInPrediction,
    ModelIsNotAvailable,
)
from app.repositories.model import model_client

logging.basicConfig(
    level=logging.INFO,
    format="\033[92m%(levelname)s\033[0m:  \t  %(message)s",
    stream=sys.stdout,
)

logger = logging.getLogger("app")


class ModerationWorker:
    def __init__(
        self,
    ):
        self.consumer: Optional[KafkaConsumer] = None
        self.producer: Optional[KafkaProducer] = None
        self.ml_service_client: Optional[MLService] = None
        self.moder_service_client: Optional[ModerationService] = None
        self.n_retries = 3

    async def start(self):
        model_client.initialize_model()
        self.consumer = await get_kafka_consumer()
        self.producer = await get_kafka_producer()
        self.ml_service_client = get_ml_service()
        self.moder_service_client = get_moder_service()

    async def stop(self):
        self.consumer.stop()
        self.producer.stop()

    async def retry(self, task_id: int, item_id: int):
        retry_count = 1
        error = ""
        original_message = ""
        while retry_count < self.n_retries:
            try:
                pred = await self.ml_service_client.simple_predict(item_id)
                await asyncio.sleep(10)
                await self.moder_service_client.complete_moderation_task(task_id, pred)
                await asyncio.sleep(5)
            except (
                ModelIsNotAvailable,
                AdvertisementNotFoundError,
                ErrorInPrediction,
            ) as e:
                error = e.__class__.__name__
                original_message = str(e)
            except Exception as e:
                error = "Exception"
                original_message = str(e)

            retry_count += 1

        await self.producer.send_to_dlq(original_message, error, retry_count)
        await self.moder_service_client.fail_moderation_task(task_id, original_message)

    async def process_moderation_request(self, message: ConsumerRecord):
        event = json.loads(message.value.decode("utf-8"))
        logger.info(
            "Process task:\n" "\ttask_id: %s" "\titem_id: %s" "\ttimestamp: %s",
            event["task_id"],
            event["item_id"],
            event["timestamp"],
        )

        try:
            pred = await self.ml_service_client.simple_predict(event["item_id"])
            await asyncio.sleep(10)
            await self.moder_service_client.complete_moderation_task(
                event["task_id"], pred
            )
        except Exception as e:
            await self.retry(event["task_id"], event["item_id"])

    async def run(self):
        await self.start()
        try:
            async for msg in self.consumer.consumer:
                await self.process_moderation_request(msg)
                await self.consumer.consumer.commit()

        finally:
            await self.stop()


async def main():
    worker = ModerationWorker()

    try:
        await worker.run()
    except KeyboardInterrupt:
        await worker.stop()


if __name__ == "__main__":
    asyncio.run(main())
