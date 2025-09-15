import logging
import time
from typing import Protocol, TypeVar, overload
import asyncio
from contextlib import asynccontextmanager
from dataclasses import asdict, dataclass
from functools import cached_property
from typing import runtime_checkable

import ninjamagic.bus as bus
from ninjamagic import conn, parser, outbox, act

TPS = 1000
STEP = 1.0 / TPS
MAX_LAG_RESET = 0.25

# for exponential moving average:
HALF_LIFE_SECONDS = 30
TICKS_PER_HALF_LIFE = int(HALF_LIFE_SECONDS * TPS)
ALPHA = 1 - 2 ** (-1 / TICKS_PER_HALF_LIFE)


log = logging.getLogger(__name__)


@runtime_checkable
class ImplementsAsyncOpen(Protocol):
    async def aopen(self) -> None: ...


@runtime_checkable
class ImplementsAsyncClose(Protocol):
    async def aclose(self) -> None: ...


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
        opens = [
            svc for svc in self.deps.values() if isinstance(svc, ImplementsAsyncOpen)
        ]
        await asyncio.gather(*[open.aopen() for open in opens])
        loop = asyncio.get_running_loop()
        loop.create_task(self.step())
        log.info("Started state.")

    async def aclose(self):
        closes = [
            svc for svc in self.deps.values() if isinstance(svc, ImplementsAsyncClose)
        ]
        await asyncio.gather(*[close.aclose() for close in closes])
        log.info("Ending state.")

    async def step(self) -> None:
        pass

    @overload
    def get(self, t1: type[T1], /) -> T1: ...

    @overload
    def get(self, t1: type[T1], t2: type[T2], /) -> tuple[T1, T2]: ...

    @overload
    def get(self, t1: type[T1], t2: type[T2], t3: type[T3], /) -> tuple[T1, T2, T3]: ...

    @overload
    def get(
        self, t1: type[T1], t2: type[T2], t3: type[T3], t4: type[T4], /
    ) -> tuple[T1, T2, T3, T4]: ...

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
        last_logged_sec = 0
        loop = asyncio.get_running_loop()
        deadline = loop.time()
        prev_ns = time.perf_counter_ns()

        jitter_ema = 0.0

        while True:
            frame_start_ns = time.perf_counter_ns()
            dt = (frame_start_ns - prev_ns) * 1e-9
            prev_ns = frame_start_ns

            # invoke systems        #
            conn.process()
            parser.process()
            act.process(loop.time())
            outbox.flush()
            bus.clear()
            #                       #

            deadline += STEP
            delay = deadline - loop.time()
            if delay > 0:
                pause = delay - 0.001
                if pause > 0:
                    await asyncio.sleep(pause)
                while True:
                    remaining = deadline - loop.time()
                    if remaining <= 0:
                        break
                    await asyncio.sleep(0)
            else:
                # We're late.
                lag = -delay
                if lag > MAX_LAG_RESET:
                    deadline = loop.time()

            now = loop.time()
            jitter = now - deadline
            jitter_ema = (1 - ALPHA) * jitter_ema + ALPHA * jitter
            current_sec = int(now)
            if current_sec % HALF_LIFE_SECONDS == 0 and current_sec != last_logged_sec:
                log.info("jitter_ema=%.6f", jitter_ema)
                last_logged_sec = current_sec
