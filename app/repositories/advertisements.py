from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from app.clients.postgres import get_pg_connection
from app.errors import AdvertisementNotFoundError

from app.models.advertisement import Advertisement, AdvertisementWithSeller


@dataclass(frozen=True)
class AdvertisementPostgresStorage:
    async def create(
        self,
        seller_id: int,
        id: str,
        name: str,
        description: str,
        category: int,
        images_qty: int,
    ) -> Mapping[str, Any]:
        query = """
            INSERT INTO advertisements (seller_id, id, name, description, category, images_qty)
            VALUES ($1, $2, $3, $4, $5, $6)
            RETURNING *
        """

        async with get_pg_connection() as connection:
            return dict(
                await connection.fetchrow(
                    query, seller_id, id, name, description, category, images_qty
                )
            )

    async def delete(self, id: int) -> Mapping[str, Any]:
        query = """
            DELETE FROM advertisements
            WHERE id = $1::INTEGER
            RETURNING *
        """

        async with get_pg_connection() as connection:
            row = await connection.fetchrow(query, id)

            if row:
                return dict(row)

            raise AdvertisementNotFoundError()

    async def select(self, id: int) -> Mapping[str, Any]:
        query = """
            SELECT 
                a.seller_id as seller_id,
                s.is_verified as is_verified_seller,
                a.id as item_id,
                a.name as name,
                a.description as description,
                a.category as category,
                a.images_qty as images_qty
            FROM advertisements as a
            JOIN sellers as s ON a.seller_id = s.id 
                AND a.id = $1::INTEGER
            LIMIT 1
        """

        async with get_pg_connection() as connection:
            row = await connection.fetchrow(query, id)

            if row:
                return dict(row)

            raise AdvertisementNotFoundError()

    async def select_many(self) -> Sequence[Mapping[str, Any]]:
        query = """
            SELECT 
                a.seller_id as seller_id,
                s.is_verified as is_verified_seller,
                a.id as item_id,
                a.name as name,
                a.description as description,
                a.category as category,
                a.images_qty as images_qty
            FROM advertisements as a
            JOIN sellers as s ON a.seller_id = s.id
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
            UPDATE advertisements
            SET {fields_str}
            WHERE id = $1::INTEGER
            RETURNING *
        """

        async with get_pg_connection() as connection:
            row = await connection.fetchrow(query, id, *args)

            if row:
                return dict(row)

            raise AdvertisementNotFoundError()


@dataclass(frozen=True)
class AdvertisementRepository:
    ad_postgres_storage: AdvertisementPostgresStorage = AdvertisementPostgresStorage()

    async def create(
        self,
        seller_id: int,
        id: str,
        name: str,
        description: str,
        category: int,
        images_qty: int,
    ) -> Advertisement:
        raw_user = await self.ad_postgres_storage.create(
            seller_id, id, name, description, category, images_qty
        )
        return Advertisement(**raw_user)

    async def get(self, item_id: int) -> AdvertisementWithSeller:
        raw_user = await self.ad_postgres_storage.select(item_id)
        return AdvertisementWithSeller(**raw_user)

    async def delete(self, item_id: int) -> Advertisement:
        raw_user = await self.ad_postgres_storage.delete(item_id)
        return Advertisement(**raw_user)

    async def update(self, item_id: int, **changes: Mapping[str, Any]) -> Advertisement:
        raw_user = await self.ad_postgres_storage.update(item_id, **changes)
        return Advertisement(**raw_user)

    async def get_many(self) -> Sequence[AdvertisementWithSeller]:
        return [
            AdvertisementWithSeller(**raw_user)
            for raw_user in await self.ad_postgres_storage.select_many()
        ]
