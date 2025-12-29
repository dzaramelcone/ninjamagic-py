from collections import defaultdict, deque

import esper

from ninjamagic import bus
from ninjamagic.component import EntityId, Lag, Prompt

pending: defaultdict[EntityId, deque[bus.Inbound]] = defaultdict(deque)
clean: list[EntityId] = []
SPAM_PENALTY: float = 0.275
DEQUE_MAXLEN = 20


def process(now: float):
    for sig in bus.iter(bus.InboundPrompt):
        esper.remove_component(sig.source, Prompt)
        if sig.prompt.end < now:
            bus.pulse(bus.Inbound(source=sig.source, text=sig.text))
            continue

        if sig.prompt.text != sig.text:
            if sig.prompt.on_mismatch:
                sig.prompt.on_mismatch()
            else:
                bus.pulse(bus.Inbound(source=sig.source, text=sig.text))
            continue

        if sig.prompt.on_success:
            sig.prompt.on_success()

    for sig in bus.iter(bus.Inbound):
        lag = esper.try_component(sig.source, Lag) or -1
        is_lagged = now < lag
        if is_lagged:
            if len(pending[sig.source]) < DEQUE_MAXLEN:
                pending[sig.source].append(sig)
            continue

        bus.pulse(bus.Parse(source=sig.source, text=sig.text))

    for entity, queue in pending.items():
        if not esper.entity_exists(entity):
            clean.append(entity)
            continue

        lag = esper.try_component(entity, Lag) or -1
        is_lagged = now < lag
        if is_lagged:
            continue

        sig = queue.popleft()
        bus.pulse(bus.Parse(source=sig.source, text=sig.text))

        if not queue:
            clean.append(entity)
        else:
            esper.add_component(entity, now + SPAM_PENALTY, Lag)

    while clean:
        entity = clean.pop()
        pending.pop(entity, None)
        esper.remove_component(entity, Lag)
