import pytest
import json
from unittest.mock import Mock, AsyncMock
from datetime import datetime
from aiokafka import ConsumerRecord

from app.workers.moderation_worker import ModerationWorker
from app.errors import (
    AdvertisementNotFoundError,
)


@pytest.fixture
def mock_consumer():
    consumer = AsyncMock()
    consumer.__aiter__.return_value = [Mock(spec=ConsumerRecord)]
    consumer.consumer = consumer
    return consumer


@pytest.fixture
def mock_producer():
    producer = AsyncMock()
    producer.send_to_dlq = AsyncMock()
    return producer


@pytest.fixture
def mock_ml_service():
    ml_service = AsyncMock()
    ml_service.simple_predict = AsyncMock()
    return ml_service


@pytest.fixture
def mock_moder_service():
    moder_service = AsyncMock()
    moder_service.complete_moderation_task = AsyncMock()
    moder_service.fail_moderation_task = AsyncMock()
    return moder_service


@pytest.fixture
def worker(mock_consumer, mock_producer, mock_ml_service, mock_moder_service):
    worker = ModerationWorker()
    worker.consumer = mock_consumer
    worker.producer = mock_producer
    worker.ml_service_client = mock_ml_service
    worker.moder_service_client = mock_moder_service
    worker.n_retries = 3
    return worker


def create_test_message(task_id: int, item_id: int, timestamp: str = None):
    if timestamp is None:
        timestamp = datetime.now().isoformat()

    value = json.dumps(
        {"task_id": task_id, "item_id": item_id, "timestamp": timestamp}
    ).encode("utf-8")

    return ConsumerRecord(
        topic="moderation",
        partition=0,
        offset=0,
        timestamp=0,
        timestamp_type=0,
        key=None,
        value=value,
        headers=[],
        checksum=None,
        serialized_key_size=-1,
        serialized_value_size=len(value),
    )


@pytest.mark.asyncio
async def test_process_moderation_request_success(worker):
    task_id = 1
    item_id = 2
    message = create_test_message(task_id, item_id)

    expected_prediction = {"is_violation": True, "probability": 0.95}
    worker.ml_service_client.simple_predict.return_value = expected_prediction

    await worker.process_moderation_request(message)

    worker.ml_service_client.simple_predict.assert_called_once_with(item_id)
    worker.moder_service_client.complete_moderation_task.assert_called_once_with(
        task_id, expected_prediction
    )
    worker.producer.send_to_dlq.assert_not_called()
    worker.moder_service_client.fail_moderation_task.assert_not_called()


@pytest.mark.asyncio
async def test_process_moderation_request_advertisement_not_found(worker):
    task_id = 1
    item_id = 999
    message = create_test_message(task_id, item_id)

    worker.ml_service_client.simple_predict.side_effect = AdvertisementNotFoundError()

    await worker.process_moderation_request(message)

    assert worker.ml_service_client.simple_predict.call_count == worker.n_retries

    worker.producer.send_to_dlq.assert_called_once()
    call_args = worker.producer.send_to_dlq.call_args[0]
    assert "AdvertisementNotFoundError" in call_args[1]
    assert call_args[2] == worker.n_retries

    worker.moder_service_client.fail_moderation_task.assert_called_once()
    assert worker.moder_service_client.fail_moderation_task.call_args[0][0] == task_id
