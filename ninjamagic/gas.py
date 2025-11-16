import heapq

import esper

from ninjamagic import bus
from ninjamagic.component import AABB, EntityId, Gas, Transform
from ninjamagic.move import can_enter
from ninjamagic.util import EIGHT_DIRS as DIRS, EPSILON, Walltime

scratch = list[tuple[tuple[int, int], float]]()
neighbors = list[tuple[int, int]]()
PQ = list[tuple[float, EntityId, Transform, AABB, Gas]]()
STEP_RATE = 1.0 / 3.0
LOSS_RATE = 1.0 / 125.0 * STEP_RATE


def create(*, map: int, y: int, x: int) -> EntityId:
    out = esper.create_entity()
    gas = {(y, x): 1.0}
    transform = Transform(map_id=map, x=x, y=y)
    aabb = AABB(top=y, bot=y, left=x, right=x)
    esper.add_component(out, gas)
    esper.add_component(out, transform)
    esper.add_component(out, aabb)
    heapq.heappush(PQ, (0.0, out, transform, aabb, gas))
    return out


def process(now: Walltime):
    for sig in bus.iter(bus.CreateGas):
        map, y, x = sig.loc
        create(map=map, y=y, x=x)

    while PQ and PQ[0][0] <= now:
        _, eid, transform, aabb, gas = heapq.heappop(PQ)

        aabb.clear()
        for point, potence in gas.items():
            y, x = point

            neighbors.clear()
            for dy, dx in DIRS:
                n = ny, nx = y + dy, x + dx
                if not can_enter(map_id=transform.map_id, y=ny, x=nx):
                    continue
                neighbors.append(n)

            count = len(neighbors) + 1
            potence = max(0, (potence - LOSS_RATE) / count)
            if potence <= EPSILON:
                continue

            scratch.append((point, potence))
            for n in neighbors:
                scratch.append((n, potence))

        gas.clear()
        while scratch:
            point, potence = scratch.pop()
            gas[point] = gas.get(point, 0.0) + potence
            y, x = point
            aabb.append(x=x, y=y)
        transform.y = aabb.top
        transform.x = aabb.left

        if not gas:
            esper.delete_entity(eid)
        else:
            heapq.heappush(PQ, (now + STEP_RATE, eid, transform, aabb, gas))
            bus.pulse(
                bus.GasUpdated(source=eid, transform=transform, aabb=aabb, gas=gas)
            )
