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

        prompt = sig.prompt
        matched = sig.prompt.text == sig.text
        expired = sig.prompt.end < now
        match (matched, expired):
            case (True, False):
                handler = prompt.on_success
            case (True, True):
                handler = prompt.on_expired_success
            case (False, False):
                handler = prompt.on_mismatch
            case (False, True):
                handler = prompt.on_expired_mismatch

        if handler:
            handler()
        else:
            bus.pulse(bus.Inbound(source=sig.source, text=sig.text))

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
