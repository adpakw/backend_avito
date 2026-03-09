from unittest.mock import AsyncMock, MagicMock

import pytest

from app.clients.postgres import get_pg_connection
from app.errors import AdvertisementNotFoundError
from app.models.advertisement import Advertisement
from app.services.close_service import CloseService


async def setup_database():
    async with get_pg_connection() as conn:
        await conn.execute(
            "DELETE FROM moderation_results WHERE item_id IN (1001, 1002)"
        )
        await conn.execute(
            "DELETE FROM advertisements WHERE id IN (1001, 1002, 1003, 1004)"
        )
        await conn.execute("DELETE FROM sellers WHERE id IN (101, 102, 103, 104)")

        await conn.execute(
            """
            INSERT INTO sellers (id, is_verified) VALUES 
            (101, true),
            (102, false),
            (103, true),
            (104, true)
        """
        )

        await conn.execute(
            """
            INSERT INTO advertisements (seller_id, id, name, description, category, images_qty, is_closed) VALUES 
            (101, 1001, 'Тестовый товар 1', 'Описание тестового товара 1', 1, 3, false),
            (102, 1002, 'Тестовый товар 2', 'Описание тестового товара 2', 2, 5, false),
            (103, 1003, 'Тестовый товар 3', 'Описание тестового товара 3', 3, 2, false),
            (104, 1004, 'Закрытый товар', 'Описание закрытого товара', 4, 1, true)
        """
        )

        await conn.execute(
            """
            INSERT INTO moderation_results (item_id, status, created_at) VALUES 
            (1001, 'pending', NOW()),
            (1002, 'completed', NOW())
        """
        )


async def teardown_database():
    async with get_pg_connection() as conn:
        await conn.execute(
            "DELETE FROM moderation_results WHERE item_id IN (1001, 1002)"
        )
        await conn.execute(
            "DELETE FROM advertisements WHERE id IN (1001, 1002, 1003, 1004, 2001)"
        )
        await conn.execute("DELETE FROM sellers WHERE id IN (101, 102, 103, 104, 201)")


@pytest.fixture
def close_service():
    service = CloseService()
    service.ad_repo = AsyncMock()
    service.moder_repo = AsyncMock()
    service.cache_repo = AsyncMock()
    service.cache_repo.delete_prediction = AsyncMock()
    return service


@pytest.fixture
def sample_ad():
    return Advertisement(
        seller_id=1,
        id=123,
        name="Test Product",
        description="Test description",
        category=5,
        images_qty=3,
        is_closed=False,
    )


class TestCloseServiceUnit:
    @pytest.mark.asyncio
    async def test_close_advertisement_success(self, close_service, sample_ad):
        item_id = 123
        closed_ad = sample_ad.model_copy()
        closed_ad.is_closed = True

        close_service.ad_repo.get.return_value = sample_ad
        close_service.ad_repo.close.return_value = closed_ad

        close_service.moder_repo.get_many.return_value = [
            MagicMock(id=1, item_id=item_id),
            MagicMock(id=2, item_id=item_id),
            MagicMock(id=3, item_id=456),
        ]

        result = await close_service.close_advertisement(item_id)

        assert result.is_closed == True
        assert result.id == item_id

        close_service.ad_repo.get.assert_called_once_with(item_id)
        close_service.ad_repo.close.assert_called_once_with(item_id)

        assert close_service.moder_repo.delete.call_count == 2
        close_service.moder_repo.delete.assert_any_call(1)
        close_service.moder_repo.delete.assert_any_call(2)

        close_service.cache_repo.delete_prediction.assert_called_once_with(item_id)

    @pytest.mark.asyncio
    async def test_close_advertisement_not_found(self, close_service):
        item_id = 999
        close_service.ad_repo.get.side_effect = AdvertisementNotFoundError()

        with pytest.raises(AdvertisementNotFoundError):
            await close_service.close_advertisement(item_id)

        close_service.ad_repo.close.assert_not_called()
        close_service.moder_repo.delete.assert_not_called()
        close_service.cache_repo.delete_prediction.assert_not_called()

    @pytest.mark.asyncio
    async def test_close_advertisement_no_moderation_tasks(
        self, close_service, sample_ad
    ):
        item_id = 123
        closed_ad = sample_ad.model_copy()
        closed_ad.is_closed = True

        close_service.ad_repo.get.return_value = sample_ad
        close_service.ad_repo.close.return_value = closed_ad
        close_service.moder_repo.get_many.return_value = []

        result = await close_service.close_advertisement(item_id)

        assert result.is_closed == True
        close_service.moder_repo.delete.assert_not_called()
        close_service.cache_repo.delete_prediction.assert_called_once_with(item_id)

    @pytest.mark.asyncio
    async def test_close_advertisement_moderation_delete_error(
        self, close_service, sample_ad
    ):
        item_id = 123
        closed_ad = sample_ad.model_copy()
        closed_ad.is_closed = True

        close_service.ad_repo.get.return_value = sample_ad
        close_service.ad_repo.close.return_value = closed_ad
        close_service.moder_repo.get_many.return_value = [
            MagicMock(id=1, item_id=item_id),
        ]
        close_service.moder_repo.delete.side_effect = Exception("DB Error")

        result = await close_service.close_advertisement(item_id)

        assert result.is_closed == True
        close_service.moder_repo.delete.assert_called_once_with(1)
        close_service.cache_repo.delete_prediction.assert_called_once_with(item_id)


@pytest.mark.integration
class TestCloseIntegration:
    @pytest.mark.asyncio
    async def test_close_advertisement_with_db_and_cache(self):
        from app.repositories.advertisements import AdvertisementRepository
        from app.repositories.cache import CacheRepository
        from app.repositories.moderation import ModerationRepository
        from app.services.close_service import CloseService

        await setup_database()
        service = CloseService()
        ad_repo = AdvertisementRepository()
        moder_repo = ModerationRepository()
        cache_repo = CacheRepository()

        test_item_id = 1001

        ad_before = await ad_repo.get(test_item_id)
        assert ad_before.is_closed == False
        assert ad_before.item_id == test_item_id

        moderations = await moder_repo.get_many()
        moder_for_item = [m for m in moderations if m.item_id == test_item_id]
        assert len(moder_for_item) > 0

        result = await service.close_advertisement(test_item_id)

        assert result.id == test_item_id
        assert result.is_closed == True

        ad_after = await ad_repo.get(test_item_id)
        assert ad_after.is_closed == True

        moderations_after = await moder_repo.get_many()
        moder_for_item_after = [
            m for m in moderations_after if m.item_id == test_item_id
        ]
        assert len(moder_for_item_after) == 0

        cached = await cache_repo.get_prediction(test_item_id)
        assert cached is None
        await teardown_database()
