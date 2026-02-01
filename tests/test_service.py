from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.repositories.advertisements import AdvertisementRepository
from app.repositories.model import model_client
from app.repositories.sellers import SellerRepository


@pytest.fixture(scope="session", autouse=True)
def initialize_model():
    model_client.initialize_model()
    yield


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def seller_repository():
    return SellerRepository()


@pytest.fixture
def advertisement_repository():
    return AdvertisementRepository()


class TestPredictions:
    def test_positive_prediction(self, client):
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
        assert data["probability"] > 0.62836
        assert data["probability"] < 0.62837

    def test_positive_simple_prediction(self, client):
        response = client.post("/simple_predict", json={"id": 5})
        data = response.json()

        assert response.status_code == 200
        assert data["is_violation"] == 1
        assert data["probability"] > 0.64056
        assert data["probability"] < 0.64057

    def test_negative_prediction(self, client):
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
        assert data["probability"] > 4.03325e-05
        assert data["probability"] < 4.03326e-05

    def test_negative_simple_prediction(self, client):
        response = client.post("/simple_predict", json={"id": 1})
        data = response.json()

        assert response.status_code == 200
        assert data["is_violation"] == 0
        assert data["probability"] > 0.00620
        assert data["probability"] < 0.00621


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


class TestUnavalibleModel:
    def test_unavailible_model(self):
        with patch("app.repositories.model.model_client._model", None):
            with patch("app.repositories.model.model_client.initialize_model", None):
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


class TestSellerRepository:
    @pytest.mark.asyncio
    async def test_get_seller(self, seller_repository: SellerRepository):
        seller = await seller_repository.get(id=2)

        assert seller.id == 2
        assert seller.is_verified == False

    @pytest.mark.asyncio
    async def test_get_many_sellers(self, seller_repository: SellerRepository):
        sellers = await seller_repository.get_many()

        ids = [seller.id for seller in sellers]
        list_is_verified = [seller.is_verified for seller in sellers]
        assert ids == [1, 2, 3]
        assert list_is_verified == [True, False, True]

    @pytest.mark.asyncio
    async def test_create_seller(self, seller_repository: SellerRepository):
        seller = await seller_repository.create(10, True)

        assert seller.id == 10
        assert seller.is_verified == True

    @pytest.mark.asyncio
    async def test_update_seller(self, seller_repository: SellerRepository):
        seller = await seller_repository.update(10, is_verified=False)

        assert seller.id == 10
        assert seller.is_verified == False

    @pytest.mark.asyncio
    async def test_delete_seller(self, seller_repository: SellerRepository):
        seller = await seller_repository.delete(10)

        assert seller.id == 10
        assert seller.is_verified == False


class TestAdvertisementRepository:
    @pytest.mark.asyncio
    async def test_get_advertisement(
        self, advertisement_repository: AdvertisementRepository
    ):
        advertisement = await advertisement_repository.get(item_id=2)

        assert advertisement.seller_id == 2
        assert advertisement.is_verified_seller == False
        assert advertisement.item_id == 2
        assert advertisement.name == "iPhone 13"
        assert advertisement.description == "Смартфон в идеальном состоянии"
        assert advertisement.category == 3
        assert advertisement.images_qty == 4

    @pytest.mark.asyncio
    async def test_create_advertisement(
        self, advertisement_repository: AdvertisementRepository
    ):
        advertisement = await advertisement_repository.create(
            2, 10, "bla bla", "description bla bla", 5, 5
        )

        assert advertisement.seller_id == 2
        assert advertisement.id == 10
        assert advertisement.name == "bla bla"
        assert advertisement.description == "description bla bla"
        assert advertisement.category == 5
        assert advertisement.images_qty == 5

    @pytest.mark.asyncio
    async def test_update_seller(
        self, advertisement_repository: AdvertisementRepository
    ):
        advertisement = await advertisement_repository.update(
            10, description="qwertyu", images_qty=10000
        )

        assert advertisement.seller_id == 2
        assert advertisement.id == 10
        assert advertisement.name == "bla bla"
        assert advertisement.description == "qwertyu"
        assert advertisement.category == 5
        assert advertisement.images_qty == 10000

    @pytest.mark.asyncio
    async def test_delete_seller(
        self, advertisement_repository: AdvertisementRepository
    ):
        advertisement = await advertisement_repository.delete(10)

        assert advertisement.seller_id == 2
        assert advertisement.id == 10
        assert advertisement.name == "bla bla"
        assert advertisement.description == "qwertyu"
        assert advertisement.category == 5
        assert advertisement.images_qty == 10000
