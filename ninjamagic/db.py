from collections.abc import AsyncGenerator
from contextvars import ContextVar
from typing import Annotated

from fastapi import Depends
from fastapi.concurrency import asynccontextmanager
from sqlalchemy.ext.asyncio import AsyncConnection, create_async_engine

from ninjamagic.config import settings
from ninjamagic.gen.query import AsyncQuerier

engine = create_async_engine(str(settings.pg), echo=False, future=True)
_TEST_CONN: ContextVar[AsyncConnection | None] = ContextVar("db_test_conn", default=None)


async def get_conn() -> AsyncGenerator[AsyncConnection]:
    if conn := _TEST_CONN.get():
        yield conn
        return
    async with engine.begin() as conn:
        yield conn


async def get_repository(
    conn: Annotated[AsyncConnection, Depends(get_conn)],
) -> AsyncQuerier:
    return AsyncQuerier(conn)


@asynccontextmanager
async def get_repository_factory() -> AsyncGenerator[AsyncQuerier]:
    if conn := _TEST_CONN.get():
        yield AsyncQuerier(conn)
        return
    async with engine.begin() as conn:
        yield AsyncQuerier(conn)


Repository = Annotated[AsyncQuerier, Depends(get_repository)]
