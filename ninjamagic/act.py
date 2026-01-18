import heapq
import itertools

import esper

from ninjamagic import bus
from ninjamagic.component import ActId, EntityId, Health, Stunned
from ninjamagic.util import Looptime

pq: list[bus.Act] = []
current: dict[EntityId, ActId] = {}


def is_busy(entity: EntityId):
    return entity in current


def being_attacked(target: EntityId):
    for act in itertools.chain(pq, bus.iter(bus.Act)):
        if target != act.target:
            continue
        if not esper.entity_exists(act.source):
            continue
        if current.get(act.source, act.id) != act.id:
            continue
        health = esper.try_component(act.source, Health)
        if health and health.condition != "normal":
            continue
        if esper.try_component(act.source, Stunned):
            continue
        return True
    return False


def attacked_by_other(source: EntityId, target: EntityId) -> bool:
    for act in itertools.chain(pq, bus.iter(bus.Act)):
        if act.source == source:
            continue
        if not esper.entity_exists(act.source):
            continue
        if current.get(act.source, act.id) != act.id:
            continue
        if act.target != target:
            continue
        health = esper.try_component(act.source, Health)
        if health and health.condition != "normal":
            continue
        if esper.try_component(act.source, Stunned):
            continue
        return True
    return False


def process(now: Looptime) -> None:
    for interrupt in bus.iter(bus.Interrupt):
        current.pop(interrupt.source, None)

    while pq and pq[0].end < now:
        act = heapq.heappop(pq)
        if current.get(act.source) == act.id:
            del current[act.source]
            if esper.entity_exists(act.source):
                bus.pulse(*act.then)

    for act in bus.iter(bus.Act):
        current[act.source] = act.id
        heapq.heappush(pq, act)
