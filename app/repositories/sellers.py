from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from app.clients.postgres import get_pg_connection

from app.errors import SellerNotFoundError
from app.models.seller import Seller


@dataclass(frozen=True)
class SellerPostgresStorage:
    async def create(self, id: int, is_verified: bool) -> Mapping[str, Any]:
        query = """
            INSERT INTO sellers (id, is_verified)
            VALUES ($1, $2)
            RETURNING *
        """

        async with get_pg_connection() as connection:
            return dict(await connection.fetchrow(query, id, is_verified))

    async def delete(self, id: int) -> Mapping[str, Any]:
        query = """
            DELETE FROM sellers
            WHERE id = $1::INTEGER
            RETURNING *
        """

        async with get_pg_connection() as connection:
            row = await connection.fetchrow(query, id)

            if row:
                return dict(row)

            raise SellerNotFoundError()

    async def select(self, id: int) -> Mapping[str, Any]:
        query = """
            SELECT *
            FROM sellers
            WHERE id = $1::INTEGER
            LIMIT 1
        """

        async with get_pg_connection() as connection:
            row = await connection.fetchrow(query, id)

            if row:
                return dict(row)

            raise SellerNotFoundError()

    async def select_many(self) -> Sequence[Mapping[str, Any]]:
        query = """
            SELECT *
            FROM sellers
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
            UPDATE sellers
            SET {fields_str}
            WHERE id = $1::INTEGER
            RETURNING *
        """

        async with get_pg_connection() as connection:
            row = await connection.fetchrow(query, id, *args)

            if row:
                return dict(row)

            raise SellerNotFoundError()


@dataclass(frozen=True)
class SellerRepository:
    seller_postgres_storage: SellerPostgresStorage = SellerPostgresStorage()

    async def create(self, id: int, is_verified: bool) -> Seller:
        raw_user = await self.seller_postgres_storage.create(id, is_verified)
        return Seller(**raw_user)

    async def get(self, id: int) -> Seller:
        raw_user = await self.seller_postgres_storage.select(id)
        return Seller(**raw_user)

    async def delete(self, id: int) -> Seller:
        raw_user = await self.seller_postgres_storage.delete(id)
        return Seller(**raw_user)

    async def update(self, id: int, **changes: Mapping[str, Any]) -> Seller:
        raw_user = await self.seller_postgres_storage.update(id, **changes)
        return Seller(**raw_user)

    async def get_many(self) -> Sequence[Seller]:
        return [
            Seller(**raw_user)
            for raw_user in await self.seller_postgres_storage.select_many()
        ]
