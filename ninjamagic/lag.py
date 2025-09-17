from collections import defaultdict, deque
from ninjamagic import bus
import esper

from ninjamagic.component import EntityId, Lag

pending: dict[EntityId, deque[bus.Inbound]] = defaultdict(deque)


def process(now: float):
    for sig in bus.iter(bus.Inbound):
        pending[sig.source].append(sig)

    for entity, queue in list(pending.items()):
        if not queue:
            pending.pop(entity)
            continue

        lag = esper.try_component(entity, Lag) or -1
        if now < lag:
            continue

        sig = queue.popleft()
        bus.pulse(bus.Parse(source=sig.source, text=sig.text))
