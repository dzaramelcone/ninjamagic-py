from collections import defaultdict, deque

import esper

from ninjamagic import bus
from ninjamagic.component import EntityId, Lag

pending: dict[EntityId, deque[bus.Inbound]] = defaultdict(deque)


def process(now: float):
    if bus.is_empty(bus.Inbound):
        return

    for sig in bus.iter(bus.Inbound):
        pending[sig.source].append(sig)

    for entity, queue in list(pending.items()):
        lag = esper.try_component(entity, Lag) or -1
        if now < lag:
            continue

        sig = queue.popleft()
        bus.pulse(bus.Parse(source=sig.source, text=sig.text))

        if not queue:
            pending.pop(entity)
