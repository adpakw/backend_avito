from unittest.mock import AsyncMock, patch, MagicMock

import pytest
from fastapi.testclient import TestClient

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
    with patch("app.services.ml_service.CacheRepository") as mock:
        cache_repo = AsyncMock()
        cache_repo.get_prediction = AsyncMock(return_value=None)
        cache_repo.set_prediction = AsyncMock(return_value=None)
        mock.return_value = cache_repo
        yield cache_repo


class TestPredictions:
    def test_positive_prediction(self, client, mock_cache):
        ad_data = {
            "seller_id": 0,
            "is_verified_seller": 0,
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
        # Обновляем ожидаемые значения на основе реальной модели
        assert data["probability"] > 0.84
        assert data["probability"] < 0.86

        mock_cache.get_prediction.assert_not_called()
        mock_cache.set_prediction.assert_not_called()

    def test_positive_simple_prediction(self, client, mock_cache):
        mock_cache.get_prediction.return_value = None
        
        # Мокаем метод simple_predict у реального синглтона
        with patch.object(ml_service_client, 'simple_predict', new_callable=AsyncMock) as mock_predict:
            expected_result = {"is_violation": 1, "probability": 0.64056}
            mock_predict.return_value = expected_result
            
            response = client.post("/simple_predict", json={"id": 5})
            data = response.json()

            assert response.status_code == 200
            assert data["is_violation"] == 1
            assert data["probability"] > 0.64
            assert data["probability"] < 0.65

            mock_cache.get_prediction.assert_called_once_with(5)
            mock_cache.set_prediction.assert_called_once()

    def test_simple_prediction_cache_hit(self, client, mock_cache):
        cached_result = {"is_violation": 1, "probability": 0.75}
        mock_cache.get_prediction.return_value = cached_result

        response = client.post("/simple_predict", json={"id": 5})
        data = response.json()

        assert response.status_code == 200
        assert data == cached_result

        mock_cache.get_prediction.assert_called_once_with(5)
        mock_cache.set_prediction.assert_not_called()

    def test_negative_prediction(self, client, mock_cache):
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
        data = response.json()

        assert response.status_code == 200
        assert data["is_violation"] == 0
        # Обновляем ожидаемые значения
        assert data["probability"] > 0.00004
        assert data["probability"] < 0.00005

    def test_negative_simple_prediction(self, client, mock_cache):
        mock_cache.get_prediction.return_value = None
        
        with patch.object(ml_service_client, 'simple_predict', new_callable=AsyncMock) as mock_predict:
            expected_result = {"is_violation": 0, "probability": 0.00620}
            mock_predict.return_value = expected_result
            
            response = client.post("/simple_predict", json={"id": 1})
            data = response.json()

            assert response.status_code == 200
            assert data["is_violation"] == 0
            assert data["probability"] > 0.006
            assert data["probability"] < 0.007

            mock_cache.get_prediction.assert_called_once_with(1)

    @pytest.mark.asyncio
    async def test_async_predict(self, client):
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
    async def test_moderation_result(self, client):
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
    # Во всех тестах валидации не используется pytest.mark.parametrize
    # т.к. разбил тесты на разные типы:
    # 1) пропущены все поля
    # 2) неверные типы для поля с числовым типом
    # 3) неверные типы для поля с строковым типом
    # 4) неверные типы для поля с булевым типом
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
        values_not_int = [
            3.14,
            True,
            (1, "a", True),
            [1, "a", True],
            {"key": 1, "val": False},
            None,
        ]

        for field in str_fields:
            for v in values_not_int:
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

        values_not_int = [
            3.14,
            12,
            "werty",
            (1, "a", True),
            [1, "a", True],
            {"key": 1, "val": False},
            None,
        ]

        for v in values_not_int:
            ad_data_tmp = ad_data.copy()
            ad_data_tmp["is_verified_seller"] = v

            response = client.post("/predict", json=ad_data_tmp)
            assert response.status_code == 422




class TestUnavailableModel:
    def test_unavailable_model(self):
        # Мокаем модель, чтобы она была недоступна
        with patch("app.services.ml_service.model_client") as mock_model_client:
            mock_model_client.predict.side_effect = Exception("Model not available")
            
            # Также мокаем cache_repo, чтобы не было обращений к реальному кэшу
            with patch("app.services.ml_service.CacheRepository") as mock_cache_class:
                mock_cache = AsyncMock()
                mock_cache_class.return_value = mock_cache
                
                client = TestClient(app)

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

