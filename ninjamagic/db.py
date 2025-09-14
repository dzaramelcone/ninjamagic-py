from typing import Annotated, AsyncGenerator

from fastapi import Depends
from sqlalchemy.ext.asyncio import create_async_engine, AsyncConnection

from ninjamagic.config import settings
from ninjamagic.gen.query import AsyncQuerier

engine = create_async_engine(str(settings.pg), echo=False, future=True)
async def get_conn() -> AsyncGenerator[AsyncConnection, None]:
    async with engine.begin() as conn:
        yield conn

async def get_repository(
        conn: Annotated[AsyncConnection, Depends(get_conn)]
) -> AsyncQuerier:
    return AsyncQuerier(conn)

Repository = Annotated[AsyncQuerier, Depends(get_repository)]