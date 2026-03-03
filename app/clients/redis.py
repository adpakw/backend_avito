import json
import logging
import os
import sys
from typing import Any, Optional

import redis.asyncio as redis
from dotenv import load_dotenv

logging.basicConfig(
    level=logging.INFO,
    format="\033[92m%(levelname)s\033[0m:  \t  %(message)s",
    stream=sys.stdout,
)

logger = logging.getLogger("app")

load_dotenv()


class RedisClient:
    def __init__(self):
        self.host = os.getenv("REDIS_HOST")
        self.port = os.getenv("REDIS_PORT")
        self.db = os.getenv("REDIS_DB")
        self.ttl = os.getenv("REDIS_TTL")
        self._client: Optional[redis.Redis] = None

    async def start(self) -> None:
        if not self._client:
            self._client = await redis.Redis(host=self.host, port=self.port, db=self.db)
            msg = f"Redis ping: {await self._client.ping()}"
            logger.info(msg)

    async def stop(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None

    async def get(self, key: str) -> Optional[Any]:
        if not self._client:
            await self.start()

        value = await self._client.get(key)
        if value:
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return value
        return None

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        if not self._client:
            await self.start()

        ttl = ttl or self.ttl
        serialized_value = json.dumps(value, default=str)
        return await self._client.setex(key, ttl, serialized_value)

    async def delete(self, key: str) -> bool:
        if not self._client:
            await self.start()

        return await self._client.delete(key) > 0

    async def delete_pattern(self, pattern: str) -> int:
        if not self._client:
            await self.start()

        cursor = 0
        deleted_count = 0

        while True:
            cursor, keys = await self._client.scan(cursor, match=pattern, count=100)
            if keys:
                deleted_count += await self._client.delete(*keys)
            if cursor == 0:
                break

        return deleted_count

    def make_key(self, prefix: str, identifier: int) -> str:
        return f"{prefix}:{identifier}"


redis_client = RedisClient()


async def get_redis_client() -> RedisClient:
    if not redis_client._client:
        await redis_client.start()
    return redis_client
