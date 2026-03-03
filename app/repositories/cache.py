import logging
import sys
from dataclasses import dataclass
from typing import Any, Dict, Optional

from app.clients.redis import redis_client

logging.basicConfig(
    level=logging.INFO,
    format="\033[92m%(levelname)s\033[0m:  \t  %(message)s",
    stream=sys.stdout,
)

logger = logging.getLogger("app")


@dataclass(frozen=True)
class PredictionCacheStorage:
    async def get_prediction(self, item_id: int) -> Optional[Dict[str, Any]]:
        key = redis_client.make_key("predict", item_id)
        cached = await redis_client.get(key)

        if cached:
            logger.info(f"Cache hit for item_id={item_id}")
            return cached

        logger.info(f"Cache miss for item_id={item_id}")
        return None

    async def set_prediction(self, item_id: int, prediction: Dict[str, Any]) -> None:
        """
        Комментарий о выборе TTL:
        - Используем TTL по умолчанию (1 час), так как:
          1. Модель может периодически переобучаться
          2. Данные объявлений могут обновляться
          3. Компромисс между актуальностью и производительностью
        - Для объявлений с высоким приоритетом можно задать меньший TTL
        - Кэшируем результаты для снижения нагрузки на БД и модель
        """
        key = redis_client.make_key("predict", item_id)
        await redis_client.set(key, prediction)
        logger.info(f"Cached prediction for item_id={item_id}")

    async def delete_prediction(self, item_id: int) -> None:
        key = redis_client.make_key("predict", item_id)
        await redis_client.delete(key)
        logger.info(f"Deleted cache for item_id={item_id}")


@dataclass(frozen=True)
class CacheRepository:
    cache_storage: PredictionCacheStorage = PredictionCacheStorage()

    async def get_prediction(self, item_id: int) -> Optional[Dict[str, Any]]:
        return await self.cache_storage.get_prediction(item_id)

    async def set_prediction(self, item_id: int, prediction: Dict[str, Any]) -> None:
        await self.cache_storage.set_prediction(item_id, prediction)

    async def delete_prediction(self, item_id: int) -> None:
        await self.cache_storage.delete_prediction(item_id)
