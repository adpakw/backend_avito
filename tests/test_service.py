from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.model import model_client


@pytest.fixture(scope="session", autouse=True)
def initialize_model():
    model_client.initialize_model()
    yield


@pytest.fixture
def client():
    return TestClient(app)


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
        with patch("app.model.model_client._model", None):
            with patch("app.model.model_client.initialize_model", None):
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
