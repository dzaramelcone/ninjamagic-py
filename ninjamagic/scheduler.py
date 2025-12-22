import heapq
from collections.abc import Generator

from ninjamagic import bus
from ninjamagic.nightclock import NightClock, NightDelta, NightTime
from ninjamagic.util import serial

Rule = Generator[NightDelta]
Cue = tuple[NightClock, int, bus.Signal, Rule | None]
pq = list[Cue]()
clock = NightClock()


def cue_at(time: NightTime, sig: bus.Signal, recur: Rule | None = None) -> None:
    eta = clock + clock.next(time)
    heapq.heappush(pq, (eta, serial(), sig, recur))


def every(delta: NightDelta, *, count: int = 1, forever: bool = False) -> Rule:
    i = 0
    while forever or i < count:
        yield delta
        i += 1


def process():
    clock.tick()
    while pq and pq[0][0] <= clock:
        due, tiebreak, sig, recur = heapq.heappop(pq)
        bus.pulse(sig)
        if not recur:
            continue
        if eta := next(recur, 0):
            heapq.heappush(pq, (due + eta, serial(), sig, recur))
