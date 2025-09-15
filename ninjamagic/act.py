import heapq
from ninjamagic import bus


pq: list[bus.Event] = []


def start_action(event: bus.Event) -> None:
    heapq.heappush(pq, (event.end, event))


def process(now: float) -> None:
    while pq and pq[0].end < now:
        bus.fire(heapq.heappop(pq).on_execute)
