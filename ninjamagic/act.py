import heapq

import esper

from ninjamagic import bus
from ninjamagic.component import ActId, EntityId
from ninjamagic.util import Looptime

pq: list[bus.Act] = []
current: dict[EntityId, ActId] = {}


def is_busy(entity: EntityId):
    return entity in current


def process(now: Looptime) -> None:
    for interrupt in bus.iter(bus.Interrupt):
        current.pop(interrupt.source, None)

    while pq and pq[0].end < now:
        act = heapq.heappop(pq)
        if current.get(act.source) == act.id:
            del current[act.source]
            if esper.entity_exists(act.source):
                bus.pulse(act.then)

    for act in bus.iter(bus.Act):
        current[act.source] = act.id
        heapq.heappush(pq, act)
