import datetime
import json
import logging
import os
import sys
from typing import Optional

from aiokafka import AIOKafkaProducer, AIOKafkaConsumer
from dotenv import load_dotenv

logging.basicConfig(
    level=logging.INFO,
    format="\033[92m%(levelname)s\033[0m:  \t  %(message)s",
    stream=sys.stdout,
)

logger = logging.getLogger("app")

load_dotenv()


class KafkaProducer:
    def __init__(self, bootstrap_servers: str, moderation_topic: str, dlq_topic: str):
        self._producer: Optional[AIOKafkaProducer] = None
        self._bootstrap = bootstrap_servers
        self._moderation_topic = moderation_topic
        self._dlq_topic = dlq_topic

    async def start(self) -> None:
        if not self._producer:
            self._producer = AIOKafkaProducer(bootstrap_servers=self._bootstrap)
            await self._producer.start()

    async def stop(self) -> None:
        if self._producer:
            await self._producer.stop()

    async def send_moderation_request(
        self, task_id: int, item_id: int, timestamp: datetime.datetime
    ):
        if not self._producer:
            await self.start()

        message = {
            "task_id": task_id,
            "item_id": item_id,
            "timestamp": timestamp.isoformat(),
        }
        data = json.dumps(message).encode("utf-8")
        await self._producer.send_and_wait(self._moderation_topic, data)

    async def send_to_dlq(self, original_message: str, error: str, retry_count: int):
        if not self._producer:
            await self.start()

        dlq_message = {
            "original_message": original_message,
            "error": error,
            "timestamp": datetime.datetime.now().isoformat(),
            "retry_count": retry_count,
        }
        data = json.dumps(dlq_message).encode("utf-8")
        await self._producer.send_and_wait(self._dlq_topic, data)


class KafkaConsumer:
    def __init__(
        self,
        bootstrap_servers: str,
        moderation_topic: str,
        moderation_consumer_group: str,
    ):
        self.consumer: Optional[AIOKafkaConsumer] = None
        self._bootstrap = bootstrap_servers
        self._moderation_topic = moderation_topic
        self._moderation_consumer_group = moderation_consumer_group

    async def start(self) -> None:
        if not self.consumer:
            self.consumer = AIOKafkaConsumer(
                self._moderation_topic,
                bootstrap_servers=self._bootstrap,
                group_id=self._moderation_consumer_group,
                enable_auto_commit=False,
                auto_offset_reset="earliest",
            )
            await self.consumer.start()

    async def stop(self) -> None:
        if self.consumer:
            await self.consumer.stop()


kafka_producer = KafkaProducer(
    bootstrap_servers=os.getenv("KAFKA_BOOTSTRAP"),
    moderation_topic=os.getenv("MODERATION_TOPIC"),
    dlq_topic=os.getenv("DLQ_TOPIC"),
)


async def get_kafka_producer() -> KafkaProducer:
    if not kafka_producer._producer:
        await kafka_producer.start()
    return kafka_producer


kafka_consumer = KafkaConsumer(
    bootstrap_servers=os.getenv("KAFKA_BOOTSTRAP"),
    moderation_topic=os.getenv("MODERATION_TOPIC"),
    moderation_consumer_group=os.getenv("CONSUMER_GROUP"),
)


async def get_kafka_consumer() -> KafkaConsumer:
    if not kafka_consumer.consumer:
        await kafka_consumer.start()
    return kafka_consumer
