import heapq
from collections.abc import Generator

import esper

from ninjamagic import bus, reach, story
from ninjamagic.component import Den, FromDen
from ninjamagic.nightclock import NightClock, NightDelta, NightTime
from ninjamagic.util import serial

Rule = Generator[NightDelta]
Cue = tuple[NightClock, int, bus.Signal, Rule | None]
pq = list[Cue]()
clock = NightClock()


def cue_at(sig: bus.Signal, at: NightClock, recur: Rule | None = None) -> None:
    heapq.heappush(pq, (at, serial(), sig, recur))


def cue(sig: bus.Signal, time: NightTime | None = None, recur: Rule | None = None) -> None:
    eta = clock + clock.next(time or NightTime())
    cue_at(sig, eta, recur)


def recurring(
    *, n_more_times: int = 0, interval: NightDelta | None = None, forever: bool = False
) -> Rule:
    interval = interval or NightDelta(nights=1)
    i = 0
    while forever or i < n_more_times:
        yield interval
        i += 1


def start() -> None:
    cue(bus.NightstormWarning(), time=NightTime(hour=1, minute=50), recur=recurring(forever=True))
    cue(bus.RestCheck(), time=NightTime(hour=6), recur=recurring(forever=True))
    cue(bus.DespawnMobs(), time=NightTime(hour=2), recur=recurring(forever=True))


def process() -> None:
    clock.to_now()
    while pq and pq[0][0] <= clock:
        due, tiebreak, sig, recur = heapq.heappop(pq)
        bus.pulse(sig)
        if not recur:
            continue
        if eta := next(recur, None):
            heapq.heappush(pq, (due + eta, serial(), sig, recur))
    # todo regional
    for _ in bus.iter(bus.NightstormWarning):
        story.echo("The worst of night approaches! Take cover!", range=reach.world)
    if not bus.is_empty(bus.DespawnMobs):
        for eid, _ in esper.get_component(FromDen):
            esper.delete_entity(eid)
        for _, den in esper.get_component(Den):
            den.clear()
