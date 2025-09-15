import heapq
from ninjamagic import bus


pq: list[bus.Act] = []
acts: dict[int, int] = {}


def process(now: float) -> None:
    while pq and pq[0].end < now:
        act = heapq.heappop(pq)
        if acts.get(act.source) == act.id:
            del acts[act.source]
            bus.pulse(act.next)

    for act in bus.iter(bus.Act):
        acts[act.source] = act.id
        heapq.heappush(pq, act)
