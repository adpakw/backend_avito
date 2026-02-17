from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from app.clients.postgres import get_pg_connection

from app.errors import ModerationTaskNotFoundError
from app.models.moderation import Moderation
import datetime


@dataclass(frozen=True)
class ModerationPostgresStorage:
    async def create(
        self, item_id: int, status: str, created_at: str
    ) -> Mapping[str, Any]:
        query = """
            INSERT INTO moderation_results (item_id, status, created_at)
            VALUES ($1, $2, $3)
            RETURNING *
        """

        async with get_pg_connection() as connection:
            return dict(await connection.fetchrow(query, item_id, status, created_at))

    async def delete(self, id: int) -> Mapping[str, Any]:
        query = """
            DELETE FROM moderation_results
            WHERE id = $1::INTEGER
            RETURNING *
        """

        async with get_pg_connection() as connection:
            row = await connection.fetchrow(query, id)

            if row:
                return dict(row)

            raise ModerationTaskNotFoundError()

    async def select(self, id: int) -> Mapping[str, Any]:
        query = """
            SELECT *
            FROM moderation_results
            WHERE id = $1::INTEGER
            LIMIT 1
        """

        async with get_pg_connection() as connection:
            row = await connection.fetchrow(query, id)

            if row:
                return dict(row)

            raise ModerationTaskNotFoundError()

    async def select_many(self) -> Sequence[Mapping[str, Any]]:
        query = """
            SELECT *
            FROM moderation_results
        """

        async with get_pg_connection() as connection:
            rows = await connection.fetch(query)

            return [dict(row) for row in rows]

    async def update(self, id: int, **updates: Any) -> Mapping[str, Any]:
        keys, args = [], []

        for key, value in updates.items():
            keys.append(key)
            args.append(value)

        fields_str = ", ".join([f"{key} = ${i + 2}" for i, key in enumerate(keys)])

        query = f"""
            UPDATE moderation_results
            SET {fields_str}
            WHERE id = $1::INTEGER
            RETURNING *
        """

        async with get_pg_connection() as connection:
            row = await connection.fetchrow(query, id, *args)

            if row:
                return dict(row)

            raise ModerationTaskNotFoundError()


@dataclass(frozen=True)
class ModerationRepository:
    moderation_postgres_storage: ModerationPostgresStorage = ModerationPostgresStorage()

    async def create(
        self, item_id: int, status: str, created_at: datetime.datetime
    ) -> Moderation:
        raw_user = await self.moderation_postgres_storage.create(
            item_id, status, created_at
        )
        return Moderation(**raw_user)

    async def get(self, id: int) -> Moderation:
        raw_user = await self.moderation_postgres_storage.select(id)
        return Moderation(**raw_user)

    async def delete(self, id: int) -> Moderation:
        raw_user = await self.moderation_postgres_storage.delete(id)
        return Moderation(**raw_user)

    async def update(self, id: int, **changes: Mapping[str, Any]) -> Moderation:
        raw_user = await self.moderation_postgres_storage.update(id, **changes)
        return Moderation(**raw_user)

    async def get_many(self) -> Sequence[Moderation]:
        return [
            Moderation(**raw_user)
            for raw_user in await self.moderation_postgres_storage.select_many()
        ]
