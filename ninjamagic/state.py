
import logging
import time
from typing import Protocol, TypeVar, overload
import asyncio
from contextlib import asynccontextmanager
from dataclasses import asdict, dataclass
from functools import cached_property
from typing import runtime_checkable

import ninjamagic.bus as bus
from ninjamagic import conn, parser, outbox
TICK_HZ = 1000
TPS = 1.0 / TICK_HZ

log = logging.getLogger(__name__)


@runtime_checkable
class ImplementsAsyncOpen(Protocol):
    async def aopen(self) -> None:
        ...

@runtime_checkable
class ImplementsAsyncClose(Protocol):
    async def aclose(self) -> None:
        ...

class UnregisteredDependency(Exception):
    pass

T1 = TypeVar("T1")
T2 = TypeVar("T2")
T3 = TypeVar("T3")
T4 = TypeVar("T4")

class BaseState:
    @cached_property
    def deps(self):
        return {type(v): v for v in asdict(self).values()}
    
    @asynccontextmanager
    async def __call__(self, app):
        try:
            app.state = self
            await self.aopen()
            yield
        finally:
            await self.aclose()
            app.state = None

    async def aopen(self):
        log.info("Starting state.")
        opens = [svc for svc in self.deps.values() if isinstance(svc, ImplementsAsyncOpen)]
        await asyncio.gather(*[open.aopen() for open in opens])
        loop = asyncio.get_running_loop()
        loop.create_task(self.step())
        log.info("Started state.")

    async def aclose(self):
        closes = [svc for svc in self.deps.values() if isinstance(svc, ImplementsAsyncClose)]
        await asyncio.gather(*[close.aclose() for close in closes])
        log.info("Ending state.")

    async def step(self) -> None:
        pass

    @overload
    def get(self, t1: type[T1], /) -> T1:
        ...

    @overload
    def get(self, t1: type[T1], t2: type[T2], /) -> tuple[T1, T2]:
        ...

    @overload
    def get(self, t1: type[T1], t2: type[T2], t3: type[T3], /) -> tuple[T1, T2, T3]:
        ...

    @overload
    def get(self, t1: type[T1], t2: type[T2], t3: type[T3], t4: type[T4], /) -> tuple[T1, T2, T3, T4]:
        ...

    def get(self, *svc_types: type) -> object:
        out = []
        for svc_type in svc_types:
            if not (dep := self.deps.get(svc_type, None)):
                raise UnregisteredDependency()
            out.append(dep)
        if len(out) == 1:
            return out[0]
        return out

@dataclass(slots=True, frozen=True)
class State(BaseState):
    async def step(self) -> None:
        log.info("Beginning core tick loop.")
        while True:
            frame_start = time.perf_counter()

            conn.process()

            parser.process()

            outbox.flush()

            bus.clear()

            elapsed = time.perf_counter() - frame_start
            sleep_for = TPS - elapsed
            if sleep_for > 0:
                await asyncio.sleep(sleep_for)
