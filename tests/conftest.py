from datetime import datetime
from unittest.mock import AsyncMock, Mock

import pytest

from app.dependencies.auth import get_current_active_account
from app.main import app
from app.models.account import Account


def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "integration: mark test as integration test (requires external services)",
    )


@pytest.fixture(autouse=True)
def mock_redis_for_unit_tests(request):
    if "integration" not in request.keywords:
        with pytest.MonkeyPatch.context() as mp:
            mock_redis = Mock()
            mock_redis.get = AsyncMock()
            mock_redis.set = AsyncMock()
            mock_redis.delete = AsyncMock()
            mock_redis.delete_pattern = AsyncMock()
            mock_redis.start = AsyncMock()
            mock_redis.stop = AsyncMock()
            mock_redis._make_key = lambda self, prefix, id: f"{prefix}:{id}"

            mp.setattr("app.clients.redis.redis_client", mock_redis)
            yield
    else:
        yield


@pytest.fixture
def test_account():
    return Account(
        id=1,
        login="testuser",
        password="hashed",
        is_blocked=False,
        created_at=datetime.now(),
    )


@pytest.fixture
def auth_override(test_account):
    app.dependency_overrides[get_current_active_account] = lambda: test_account
    yield
    app.dependency_overrides.pop(get_current_active_account, None)
