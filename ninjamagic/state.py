import asyncio
import logging
import time
from contextlib import asynccontextmanager

import esper

import ninjamagic.bus as bus
from ninjamagic import (
    act,
    combat,
    conn,
    emit,
    experience,
    lag,
    move,
    outbox,
    parser,
    visibility,
)

TPS = 1000
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
        loop = asyncio.get_running_loop()
        loop.create_task(self.step())
        log.info("Started state.")

    async def aclose(self):
        log.info("Ending state.")
        log.info("Ended state.")

    async def step(self) -> None:
        last_logged_sec = 0
        loop = asyncio.get_running_loop()
        deadline = loop.time()
        prev_ns = time.perf_counter_ns()

        jitter_ema = 0.0

        while True:
            frame_start_ns = time.perf_counter_ns()
            _ = (frame_start_ns - prev_ns) * 1e-9  # dt
            prev_ns = frame_start_ns

            # invoke systems        #
            conn.process()
            lag.process(now=loop.time())
            parser.process()
            act.process(now=loop.time())
            combat.process()
            move.process()
            visibility.process()
            experience.process()
            emit.process()
            outbox.process()
            bus.clear()
            esper.clear_dead_entities()
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
                late = -delay
                if late > MAX_LATE_RESET:
                    deadline = loop.time()

            now = loop.time()
            jitter = now - deadline
            jitter_ema = (1 - ALPHA) * jitter_ema + ALPHA * jitter
            current_sec = int(now)
            if current_sec % HALF_LIFE_SECONDS == 0 and current_sec != last_logged_sec:
                log.info("jitter_ema=%.6f", jitter_ema)
                last_logged_sec = current_sec
