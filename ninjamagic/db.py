from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import Depends
from fastapi.concurrency import asynccontextmanager
from sqlalchemy.ext.asyncio import AsyncConnection, create_async_engine

from ninjamagic.config import settings
from ninjamagic.gen.query import AsyncQuerier

engine = create_async_engine(str(settings.pg), echo=False, future=True)


async def get_conn() -> AsyncGenerator[AsyncConnection]:
    async with engine.begin() as conn:
        yield conn


async def get_repository(
    conn: Annotated[AsyncConnection, Depends(get_conn)],
) -> AsyncQuerier:
    return AsyncQuerier(conn)


@asynccontextmanager
async def get_repository_factory() -> AsyncGenerator[AsyncQuerier]:
    async with engine.begin() as conn:
        yield AsyncQuerier(conn)


Repository = Annotated[AsyncQuerier, Depends(get_repository)]
