from dataclasses import dataclass
from typing import Any, Mapping, Optional, Sequence

from passlib.hash import md5_crypt

from app.clients.postgres import get_pg_connection
from app.errors import AccountBlockedError, AccountNotFoundError
from app.models.account import Account
from app.observability.metrics import track_db_query


@dataclass(frozen=True)
class AccountPostgresStorage:
    @track_db_query("insert")
    async def create(self, login: str, password: str) -> Mapping[str, Any]:
        hashed_password = md5_crypt.hash(password)
        query = """
            INSERT INTO accounts (login, password, is_blocked)
            VALUES ($1, $2, $3)
            RETURNING *
        """

        async with get_pg_connection() as connection:
            return dict(await connection.fetchrow(query, login, hashed_password, False))

    @track_db_query("select")
    async def get_by_id(self, id: int) -> Mapping[str, Any]:
        query = """
            SELECT *
            FROM accounts
            WHERE id = $1::INTEGER
        """

        async with get_pg_connection() as connection:
            row = await connection.fetchrow(query, id)
            if row:
                return dict(row)
            raise AccountNotFoundError(f"Account with id {id} not found")

    @track_db_query("select")
    async def get_by_login(self, login: str) -> Optional[Mapping[str, Any]]:
        query = """
            SELECT *
            FROM accounts
            WHERE login = $1
        """

        async with get_pg_connection() as connection:
            row = await connection.fetchrow(query, login)
            return dict(row) if row else None

    @track_db_query("select")
    async def get_by_login_and_password(
        self, login: str, password: str
    ) -> Optional[Mapping[str, Any]]:
        account = await self.get_by_login(login)
        if not account:
            return None

        if md5_crypt.verify(password, account["password"]):
            return account
        return None

    @track_db_query("delete")
    async def delete(self, id: int) -> Mapping[str, Any]:
        query = """
            DELETE FROM accounts
            WHERE id = $1::INTEGER
            RETURNING *
        """

        async with get_pg_connection() as connection:
            row = await connection.fetchrow(query, id)
            if row:
                return dict(row)
            raise AccountNotFoundError(f"Account with id {id} not found")

    @track_db_query("update")
    async def block(self, id: int, block: bool = True) -> Mapping[str, Any]:
        query = """
            UPDATE accounts
            SET is_blocked = $2
            WHERE id = $1::INTEGER
            RETURNING *
        """

        async with get_pg_connection() as connection:
            row = await connection.fetchrow(query, id, block)
            if row:
                return dict(row)
            raise AccountNotFoundError(f"Account with id {id} not found")

    @track_db_query("select_many")
    async def get_all(self) -> Sequence[Mapping[str, Any]]:
        query = """
            SELECT *
            FROM accounts
            ORDER BY id
        """

        async with get_pg_connection() as connection:
            rows = await connection.fetch(query)
            return [dict(row) for row in rows]


@dataclass(frozen=True)
class AccountRepository:
    storage: AccountPostgresStorage = AccountPostgresStorage()

    async def create(self, login: str, password: str) -> Account:
        data = await self.storage.create(login, password)
        return Account(**data)

    async def get_by_id(self, id: int) -> Account:
        data = await self.storage.get_by_id(id)
        return Account(**data)

    async def get_by_login(self, login: str) -> Optional[Account]:
        data = await self.storage.get_by_login(login)
        return Account(**data) if data else None

    async def authenticate(self, login: str, password: str) -> Optional[Account]:
        data = await self.storage.get_by_login_and_password(login, password)
        if not data:
            return None

        account = Account(**data)
        if account.is_blocked:
            raise AccountBlockedError(f"Account {login} is blocked")

        return account

    async def delete(self, id: int) -> Account:
        data = await self.storage.delete(id)
        return Account(**data)

    async def block(self, id: int, block: bool = True) -> Account:
        data = await self.storage.block(id, block)
        return Account(**data)

    async def get_all(self) -> Sequence[Account]:
        data_list = await self.storage.get_all()
        return [Account(**data) for data in data_list]
