import heapq
from ninjamagic import bus


pq: list[bus.Act] = []
acts: dict[int, int] = {}


def start_act(act: bus.Act) -> None:
    acts[act.source] = act.id
    heapq.heappush(pq, act)


def process(now: float) -> None:
    while pq and pq[0].end < now:
        act = heapq.heappop(pq)
        if acts.get(act.source) == act.id:
            del acts[act.source]
            bus.fire(act.next)
