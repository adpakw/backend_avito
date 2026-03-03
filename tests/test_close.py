import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from app.services.close_service import CloseService
from app.models.advertisement import Advertisement
from app.errors import AdvertisementNotFoundError


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
        is_closed=False
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
    async def test_close_advertisement_no_moderation_tasks(self, close_service, sample_ad):
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
    async def test_close_advertisement_moderation_delete_error(self, close_service, sample_ad):
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
        
        from app.services.close_service import CloseService
        from app.repositories.advertisements import AdvertisementRepository
        from app.repositories.moderation import ModerationRepository
        from app.repositories.cache import CacheRepository
        
        service = CloseService()
        ad_repo = AdvertisementRepository()
        moder_repo = ModerationRepository()
        cache_repo = CacheRepository()
        
        test_item_id = 9999
        
        result = await service.close_advertisement(test_item_id)
        
        assert result.id == test_item_id
        assert result.is_closed == True
        
        ad = await ad_repo.get(test_item_id)
        assert ad.is_closed == True
        
        cached = await cache_repo.get_prediction(test_item_id)
        assert cached is None