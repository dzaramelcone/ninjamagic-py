import asyncio
import logging
import time
from contextlib import asynccontextmanager
from typing import Annotated

import esper
import httpx
from fastapi import Depends, Request

import ninjamagic.bus as bus
from ninjamagic import (
    act,
    combat,
    conn,
    cook,
    echo,
    experience,
    forage,
    gas,
    inbound,
    move,
    outbox,
    parser,
    proc,
    regen,
    scheduler,
    survive,
    visibility,
)
from ninjamagic.util import get_looptime

TPS = 240.0
STEP = 1.0 / TPS
MAX_LATE_RESET = 0.25

# for exponential moving average:
HALF_LIFE_SECONDS = 30
TICKS_PER_HALF_LIFE = int(HALF_LIFE_SECONDS * TPS)
ALPHA = 1 - 2 ** (-1 / TICKS_PER_HALF_LIFE)


log = logging.getLogger(__name__)


class State:
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
        self.client = httpx.AsyncClient()
        loop = asyncio.get_running_loop()
        loop.create_task(self.step())
        log.info("Started state.")

    async def aclose(self):
        log.info("Ending state.")
        await self.client.aclose()
        log.info("Ended state.")

    async def step(self) -> None:
        last_logged_sec = 0
        now = deadline = get_looptime()
        prev_ns = time.perf_counter_ns()

        jitter_ema = 0.0

        scheduler.start()

        while True:
            frame_start_ns = time.perf_counter_ns()
            _ = (frame_start_ns - prev_ns) * 1e-9  # dt
            prev_ns = frame_start_ns

            # invoke systems        #
            scheduler.process()
            conn.process()
            inbound.process(now=now)
            parser.process()
            regen.process(now=now)
            gas.process(now=now)
            act.process(now=now)
            forage.process()
            cook.process()
            survive.process()
            combat.process(now=now)
            proc.process(now=now)
            move.process()
            visibility.process()
            experience.process()
            echo.process()
            outbox.process()
            bus.clear()
            #                       #
            esper.clear_dead_entities()

            deadline += STEP
            delay = deadline - get_looptime()
            if delay > 0:
                pause = delay - 0.001
                if pause > 0:
                    await asyncio.sleep(pause)
                while True:
                    remaining = deadline - get_looptime()
                    if remaining <= 0:
                        break
                    await asyncio.sleep(0)
            else:
                # We're late.
                late = -delay
                if late > MAX_LATE_RESET:
                    deadline = get_looptime()

            now = get_looptime()
            jitter = now - deadline
            jitter_ema = (1 - ALPHA) * jitter_ema + ALPHA * jitter
            current_sec = int(now)
            if current_sec % HALF_LIFE_SECONDS == 0 and current_sec != last_logged_sec:
                log.info("jitter_ema=%.6f", jitter_ema)
                last_logged_sec = current_sec


async def get_http_client(request: Request) -> httpx.AsyncClient:
    if not hasattr(request.app.state, "client"):
        raise RuntimeError("App state is not initialized with http client")
    return request.app.state.client


ClientDep = Annotated[httpx.AsyncClient, Depends(get_http_client)]
