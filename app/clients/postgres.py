import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import asyncpg
from dotenv import load_dotenv


@asynccontextmanager
async def get_pg_connection() -> AsyncGenerator[None, asyncpg.Connection]:
    # TODO: 1. При каждом обращении к БД создается новое соединение
    # TODO: 2. Не учитывается работа в транзакции

    load_dotenv()

    connection: asyncpg.Connection = await asyncpg.connect(
        user=os.getenv("POSTGRES_USER"),
        password=os.getenv("POSTGRES_PASSWORD"),
        database=os.getenv("POSTGRES_DB"),
        host="localhost",
        port=os.getenv("POSTGRES_PORT"),
    )

    yield connection

    await connection.close()
