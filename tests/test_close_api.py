from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.errors import AdvertisementNotFoundError
from app.main import app
from app.models.advertisement import Advertisement
from app.services.close_service import close_service_client


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def sample_ad():
    return Advertisement(
        seller_id=1,
        id=123,
        name="Test Product",
        description="Test description",
        category=5,
        images_qty=3,
        is_closed=True,
    )


class TestCloseAPI:
    def test_close_advertisement_success(self, client, sample_ad):
        with patch.object(
            close_service_client, "close_advertisement", new_callable=AsyncMock
        ) as mock_close:
            mock_close.return_value = sample_ad

            request_data = {"id": 123}

            response = client.post("/close", json=request_data)

            assert response.status_code == 200
            data = response.json()
            assert data["id"] == 123
            assert data["is_closed"] == True
            assert data["name"] == "Test Product"

            mock_close.assert_called_once_with(123)

    def test_close_advertisement_not_found(self, client):
        with patch.object(
            close_service_client, "close_advertisement", new_callable=AsyncMock
        ) as mock_close:
            # Настраиваем мок на выброс исключения
            mock_close.side_effect = AdvertisementNotFoundError()

            request_data = {"id": 99999}

            response = client.post("/close", json=request_data)

            assert response.status_code == 404
            data = response.json()
            assert "detail" in data

            mock_close.assert_called_once_with(99999)

    def test_close_advertisement_invalid_input(self, client):
        request_data = {"id": -1}

        response = client.post("/close", json=request_data)

        assert response.status_code == 422

    def test_close_advertisement_missing_field(self, client):
        request_data = {}

        response = client.post("/close", json=request_data)

        assert response.status_code == 422