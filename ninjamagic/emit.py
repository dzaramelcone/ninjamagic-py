import esper

from ninjamagic import bus
from ninjamagic.component import Connection, Transform


def process():
    if bus.is_empty(bus.Emit):
        return

    clients = esper.get_components(Connection, Transform)
    for sig in bus.iter(bus.Emit):
        origin = esper.try_component(sig.source, Transform)
        if not origin:  # TODO: some reaches wont care.
            continue

        for eid, comps in clients:
            _, pos = comps
            if sig.source == eid:
                continue
            if sig.target_text and sig.target == eid:
                bus.pulse(bus.Outbound(to=eid, text=sig.target_text))
                continue

            if sig.range(origin, pos):
                bus.pulse(bus.Outbound(to=eid, text=sig.text))
