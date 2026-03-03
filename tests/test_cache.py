from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.advertisement import AdvertisementWithSeller
from app.repositories.cache import CacheRepository, PredictionCacheStorage
from app.services.ml_service import MLService


@pytest.fixture
def mock_redis_client():
    with patch("app.repositories.cache.redis_client") as mock:
        mock.get = AsyncMock()
        mock.set = AsyncMock()
        mock.delete = AsyncMock()
        mock.delete_pattern = AsyncMock()
        mock.make_key = MagicMock(side_effect=lambda prefix, id: f"{prefix}:{id}")
        yield mock


@pytest.fixture
def cache_storage(mock_redis_client):
    with patch("app.repositories.cache.redis_client", mock_redis_client):
        storage = PredictionCacheStorage()
        yield storage


@pytest.fixture
def cache_repo(cache_storage):
    return CacheRepository(cache_storage=cache_storage)


@pytest.fixture
def ml_service():
    service = MLService()
    service.cache_repo = AsyncMock(spec=CacheRepository)
    service.model_client = MagicMock()
    service.model_client.predict = MagicMock(return_value=(1, 0.85))
    return service


@pytest.fixture
def sample_ad():
    return AdvertisementWithSeller(
        seller_id=1,
        is_verified_seller=True,
        item_id=123,
        name="Test Product",
        description="Test description",
        category=5,
        images_qty=3,
    )


class TestCacheStorageUnit:
    @pytest.mark.asyncio
    async def test_get_prediction_cache_hit(self, cache_storage, mock_redis_client):
        item_id = 123
        expected_result = {"is_violation": 1, "probability": 0.85}
        mock_redis_client.get.return_value = expected_result

        result = await cache_storage.get_prediction(item_id)

        assert result == expected_result
        mock_redis_client.get.assert_called_once_with(f"predict:{item_id}")

    @pytest.mark.asyncio
    async def test_get_prediction_cache_miss(self, cache_storage, mock_redis_client):
        item_id = 123
        mock_redis_client.get.return_value = None

        result = await cache_storage.get_prediction(item_id)

        assert result is None
        mock_redis_client.get.assert_called_once_with(f"predict:{item_id}")

    @pytest.mark.asyncio
    async def test_set_prediction(self, cache_storage, mock_redis_client):
        item_id = 123
        prediction = {"is_violation": 1, "probability": 0.85}
        mock_redis_client.set.return_value = True

        await cache_storage.set_prediction(item_id, prediction)

        mock_redis_client.set.assert_called_once_with(f"predict:{item_id}", prediction)

    @pytest.mark.asyncio
    async def test_delete_prediction(self, cache_storage, mock_redis_client):
        item_id = 123
        mock_redis_client.delete.return_value = True

        await cache_storage.delete_prediction(item_id)

        mock_redis_client.delete.assert_called_once_with(f"predict:{item_id}")


class TestCacheRepository:
    @pytest.mark.asyncio
    async def test_get_prediction(self):
        mock_storage = AsyncMock(spec=PredictionCacheStorage)
        mock_storage.get_prediction = AsyncMock()

        repo = CacheRepository(cache_storage=mock_storage)

        item_id = 123
        expected = {"is_violation": 1, "probability": 0.85}
        mock_storage.get_prediction.return_value = expected

        result = await repo.get_prediction(item_id)

        assert result == expected
        mock_storage.get_prediction.assert_called_once_with(item_id)

    @pytest.mark.asyncio
    async def test_set_prediction(self):
        mock_storage = AsyncMock(spec=PredictionCacheStorage)
        mock_storage.set_prediction = AsyncMock()

        repo = CacheRepository(cache_storage=mock_storage)

        item_id = 123
        prediction = {"is_violation": 1, "probability": 0.85}

        await repo.set_prediction(item_id, prediction)

        mock_storage.set_prediction.assert_called_once_with(item_id, prediction)

    @pytest.mark.asyncio
    async def test_delete_prediction(self):
        mock_storage = AsyncMock(spec=PredictionCacheStorage)
        mock_storage.delete_prediction = AsyncMock()

        repo = CacheRepository(cache_storage=mock_storage)

        item_id = 123

        await repo.delete_prediction(item_id)

        mock_storage.delete_prediction.assert_called_once_with(item_id)


class TestMLServiceWithCache:
    @pytest.mark.asyncio
    async def test_simple_predict_cache_hit(self, ml_service):
        item_id = 123
        cached_result = {"is_violation": 1, "probability": 0.85}
        ml_service.cache_repo.get_prediction.return_value = cached_result

        result = await ml_service.simple_predict(item_id)

        assert result == cached_result
        ml_service.cache_repo.get_prediction.assert_called_once_with(item_id)
        ml_service.cache_repo.set_prediction.assert_not_called()

    @pytest.mark.asyncio
    async def test_simple_predict_cache_miss(self, ml_service):
        item_id = 123
        ml_service.cache_repo.get_prediction.return_value = None

        with patch(
            "app.services.ml_service.AdvertisementRepository"
        ) as mock_ad_repo_class:
            mock_ad_repo = AsyncMock()
            mock_ad_repo.get.return_value = AdvertisementWithSeller(
                seller_id=1,
                is_verified_seller=True,
                item_id=item_id,
                name="Test",
                description="Test",
                category=5,
                images_qty=3,
            )
            mock_ad_repo_class.return_value = mock_ad_repo

            result = await ml_service.simple_predict(item_id)

            assert result == {"is_violation": 1, "probability": 0.85}
            ml_service.cache_repo.get_prediction.assert_called_once_with(item_id)
            ml_service.cache_repo.set_prediction.assert_called_once_with(
                item_id, result
            )
            mock_ad_repo.get.assert_called_once_with(item_id)

    @pytest.mark.asyncio
    async def test_invalidate_cache(self, ml_service):
        item_id = 123

        await ml_service.invalidate_cache(item_id)

        ml_service.cache_repo.delete_prediction.assert_called_once_with(item_id)


@pytest.mark.integration
class TestCacheIntegration:
    @pytest.mark.asyncio
    async def test_redis_integration(self):

        from app.clients.redis import redis_client
        from app.repositories.cache import PredictionCacheStorage

        await redis_client.start()

        try:
            storage = PredictionCacheStorage()
            item_id = 9999
            prediction = {"is_violation": 1, "probability": 0.95}

            await storage.set_prediction(item_id, prediction)

            cached = await storage.get_prediction(item_id)
            assert cached == prediction

            await storage.delete_prediction(item_id)
            cached = await storage.get_prediction(item_id)
            assert cached is None

        finally:
            await redis_client.stop()
