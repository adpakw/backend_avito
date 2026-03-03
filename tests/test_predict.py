from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.errors import ModelIsNotAvailable
from app.main import app
from app.repositories.model import model_client
from app.repositories.moderation import ModerationRepository
from app.services.ml_service import ml_service_client


@pytest.fixture(scope="session", autouse=True)
def initialize_model():
    model_client.initialize_model()
    yield


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def mock_cache():
    cache_repo = AsyncMock()
    cache_repo.get_prediction = AsyncMock(return_value=None)
    cache_repo.set_prediction = AsyncMock(return_value=None)
    cache_repo.delete_prediction = AsyncMock(return_value=None)

    original_cache_repo = ml_service_client.cache_repo
    ml_service_client.cache_repo = cache_repo

    yield cache_repo

    ml_service_client.cache_repo = original_cache_repo


@pytest.fixture
def mock_ad_repo():
    with patch("app.services.ml_service.AdvertisementRepository") as mock_ad_repo_class:
        ad_repo = AsyncMock()
        ad_repo.get = AsyncMock()
        mock_ad_repo_class.return_value = ad_repo
        yield ad_repo


@pytest.fixture
def mock_model():
    original_model_client = ml_service_client.model_client
    mock_model = MagicMock()
    mock_model.predict = MagicMock()
    ml_service_client.model_client = mock_model
    yield mock_model
    ml_service_client.model_client = original_model_client


@pytest.fixture
def reset_ml_service():
    original_cache_repo = ml_service_client.cache_repo
    original_model_client = ml_service_client.model_client

    yield

    ml_service_client.cache_repo = original_cache_repo
    ml_service_client.model_client = original_model_client


class TestPredictions:
    def test_positive_prediction(self, client, mock_cache, reset_ml_service):
        ad_data = {
            "seller_id": 0,
            "is_verified_seller": False,
            "item_id": 123,
            "name": "Product 1",
            "description": "bla bla bla",
            "category": 100,
            "images_qty": 1,
        }

        response = client.post("/predict", json=ad_data)
        data = response.json()

        assert response.status_code == 200
        assert data["is_violation"] == 1
        assert 0.84 < data["probability"] < 0.86

        mock_cache.get_prediction.assert_not_called()
        mock_cache.set_prediction.assert_not_called()

    def test_positive_simple_prediction(
        self, client, mock_cache, mock_ad_repo, mock_model, reset_ml_service
    ):
        mock_cache.get_prediction.return_value = None

        from app.models.advertisement import AdvertisementWithSeller

        test_ad = AdvertisementWithSeller(
            seller_id=1,
            is_verified_seller=True,
            item_id=5,
            name="Test",
            description="Test description",
            category=5,
            images_qty=3,
            is_closed=False,
        )
        mock_ad_repo.get.return_value = test_ad

        expected_result = (1, 0.64056)
        mock_model.predict.return_value = expected_result

        response = client.post("/simple_predict", json={"id": 5})
        data = response.json()

        assert response.status_code == 200
        assert data["is_violation"] == 1
        assert 0.64 < data["probability"] < 0.65

        mock_cache.get_prediction.assert_called_once_with(5)
        mock_ad_repo.get.assert_called_once_with(5)
        mock_model.predict.assert_called_once()
        mock_cache.set_prediction.assert_called_once_with(
            5, {"is_violation": 1, "probability": 0.64056}
        )

    def test_simple_prediction_cache_hit(
        self, client, mock_cache, mock_ad_repo, mock_model, reset_ml_service
    ):
        cached_result = {"is_violation": 1, "probability": 0.75}
        mock_cache.get_prediction.return_value = cached_result

        response = client.post("/simple_predict", json={"id": 5})
        data = response.json()

        assert response.status_code == 200
        assert data == cached_result

        mock_cache.get_prediction.assert_called_once_with(5)
        mock_ad_repo.get.assert_not_called()
        mock_model.predict.assert_not_called()
        mock_cache.set_prediction.assert_not_called()

    def test_negative_prediction(self, client, mock_cache, reset_ml_service):
        ad_data = {
            "seller_id": 0,
            "is_verified_seller": True,
            "item_id": 123,
            "name": "Product 1",
            "description": "bla bla bla" * 100,
            "category": 100,
            "images_qty": 10,
        }

        response = client.post("/predict", json=ad_data)
        data = response.json()

        assert response.status_code == 200
        assert "is_violation" in data
        assert "probability" in data

    def test_negative_simple_prediction(
        self, client, mock_cache, mock_ad_repo, mock_model, reset_ml_service
    ):
        mock_cache.get_prediction.return_value = None

        from app.models.advertisement import AdvertisementWithSeller

        test_ad = AdvertisementWithSeller(
            seller_id=2,
            is_verified_seller=False,
            item_id=1,
            name="Test",
            description="Test description",
            category=5,
            images_qty=3,
            is_closed=False,
        )
        mock_ad_repo.get.return_value = test_ad

        mock_model.predict.return_value = (0, 0.00620)

        response = client.post("/simple_predict", json={"id": 1})
        data = response.json()

        assert response.status_code == 200
        assert data["is_violation"] == 0
        assert 0.006 < data["probability"] < 0.007

        mock_cache.get_prediction.assert_called_once_with(1)
        mock_ad_repo.get.assert_called_once_with(1)
        mock_model.predict.assert_called_once()
        mock_cache.set_prediction.assert_called_once_with(
            1, {"is_violation": 0, "probability": 0.00620}
        )

    @pytest.mark.asyncio
    async def test_async_predict(self, client, reset_ml_service):
        moder_repo = ModerationRepository()
        moderations = await moder_repo.get_many()
        moderations_ids = [moderation.id for moderation in moderations]
        max_moderations_id = max(moderations_ids) if moderations_ids else 0

        response = client.post("/async_predict", json={"id": 1})
        data = response.json()

        assert data["task_id"] > max_moderations_id
        assert data["status"] == "pending"
        assert data["message"] == "Moderation request accepted"

        moder_res = await moder_repo.get(data["task_id"])
        assert moder_res.id == data["task_id"]
        assert moder_res.item_id == 1
        assert moder_res.status == "pending"
        assert moder_res.is_violation is None
        assert moder_res.probability is None
        assert moder_res.error_message is None

    @pytest.mark.asyncio
    async def test_moderation_result(self, client, reset_ml_service):
        moder_repo = ModerationRepository()
        moderations = await moder_repo.get_many()
        moderations_ids = [moderation.id for moderation in moderations]
        if not moderations_ids:
            pytest.skip("No moderation tasks found")

        max_moderations_id = max(moderations_ids)
        moderation = await moder_repo.get(max_moderations_id)

        response = client.get(f"/moderation_result/{max_moderations_id}")
        data = response.json()

        assert response.status_code == 200
        assert data["task_id"] == moderation.id
        assert data["status"] == moderation.status
        assert data["is_violation"] == moderation.is_violation
        assert data["probability"] == moderation.probability


class TestValidation:
    def test_missing_required_field(self, client):
        ad_data = {
            "seller_id": 4,
            "is_verified_seller": False,
            "item_id": 1234567,
            "name": "Product 5",
            "description": "zxcvbnm",
            "category": 4,
            "images_qty": 0,
        }

        for field in ad_data.keys():
            ad_data_tmp = ad_data.copy()
            ad_data_tmp.pop(field)

            response = client.post("/predict", json=ad_data_tmp)
            assert response.status_code == 422

    def test_wrong_type_for_int_fields(self, client):
        ad_data = {
            "seller_id": 4,
            "is_verified_seller": False,
            "item_id": 1234567,
            "name": "Product 5",
            "description": "zxcvbnm",
            "category": 4,
            "images_qty": 0,
        }

        int_fields = ["seller_id", "item_id", "category", "images_qty"]
        values_not_int = [
            3.14,
            "hello",
            (1, "a", True),
            [1, "a", True],
            {"key": 1, "val": False},
            None,
        ]

        for field in int_fields:
            for v in values_not_int:
                ad_data_tmp = ad_data.copy()
                ad_data_tmp[field] = v

                response = client.post("/predict", json=ad_data_tmp)
                assert response.status_code == 422

    def test_wrong_type_for_str_fields(self, client):
        ad_data = {
            "seller_id": 4,
            "is_verified_seller": False,
            "item_id": 1234567,
            "name": "Product 5",
            "description": "zxcvbnm",
            "category": 4,
            "images_qty": 0,
        }

        str_fields = ["name", "description"]
        values_not_str = [
            3.14,
            True,
            (1, "a", True),
            [1, "a", True],
            {"key": 1, "val": False},
            None,
        ]

        for field in str_fields:
            for v in values_not_str:
                ad_data_tmp = ad_data.copy()
                ad_data_tmp[field] = v

                response = client.post("/predict", json=ad_data_tmp)
                assert response.status_code == 422

    def test_wrong_type_for_bool_fields(self, client):
        ad_data = {
            "seller_id": 4,
            "is_verified_seller": False,
            "item_id": 1234567,
            "name": "Product 5",
            "description": "zxcvbnm",
            "category": 4,
            "images_qty": 0,
        }

        values_not_bool = [
            3.14,
            12,
            "werty",
            (1, "a", True),
            [1, "a", True],
            {"key": 1, "val": False},
            None,
        ]

        for v in values_not_bool:
            ad_data_tmp = ad_data.copy()
            ad_data_tmp["is_verified_seller"] = v

            response = client.post("/predict", json=ad_data_tmp)
            assert response.status_code == 422


class TestUnavailableModel:
    def test_unavailable_model(
        self, client, mock_cache, mock_ad_repo, mock_model, reset_ml_service
    ):
        mock_model.predict.side_effect = ModelIsNotAvailable("Model not loaded")

        ad_data = {
            "seller_id": 0,
            "is_verified_seller": True,
            "item_id": 123,
            "name": "Product 1",
            "description": "bla bla bla",
            "category": 100,
            "images_qty": 10,
        }

        response = client.post("/predict", json=ad_data)

        assert response.status_code == 503
        assert "Model is not available" in response.json()["detail"]
