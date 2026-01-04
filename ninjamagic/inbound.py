from collections import defaultdict, deque

import esper

from ninjamagic import bus
from ninjamagic.component import EntityId, Lag, Prompt
from ninjamagic.util import Looptime

pending: defaultdict[EntityId, deque[bus.Inbound]] = defaultdict(deque)
clean_up: list[EntityId] = []
SPAM_PENALTY: float = 0.275
DEQUE_MAXLEN = 20


def process(now: Looptime):
    for sig in bus.iter(bus.InboundPrompt):
        esper.remove_component(sig.source, Prompt)

        prompt = sig.prompt
        matched = sig.prompt.text == sig.text
        expired = sig.prompt.end and sig.prompt.end < now
        match (matched, expired):
            case (True, False):
                handler = prompt.on_ok
            case (False, False):
                handler = prompt.on_err
            case (True, True):
                handler = prompt.on_expired_ok
            case (False, True):
                handler = prompt.on_expired_err

        if handler:
            handler(source=sig.source)
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
            clean_up.append(entity)
            continue

        lag = esper.try_component(entity, Lag) or -1
        is_lagged = now < lag
        if is_lagged:
            continue

        sig = queue.popleft()
        bus.pulse(bus.Parse(source=sig.source, text=sig.text))

        if not queue:
            clean_up.append(entity)
        else:
            esper.add_component(entity, now + SPAM_PENALTY, Lag)

    while clean_up:
        entity = clean_up.pop()
        pending.pop(entity, None)
        esper.remove_component(entity, Lag)
