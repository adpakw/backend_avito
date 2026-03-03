import pytest
from unittest.mock import Mock, AsyncMock


def pytest_configure(config):
    """Конфигурация pytest с маркерами"""
    config.addinivalue_line(
        "markers",
        "integration: mark test as integration test (requires external services)"
    )


@pytest.fixture(autouse=True)
def mock_redis_for_unit_tests(request):
    """
    Автоматически мокаем Redis для всех юнит-тестов.
    Для интеграционных тестов не мокаем.
    """
    if "integration" not in request.keywords:
        with pytest.MonkeyPatch.context() as mp:
            # Мокаем redis_client
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