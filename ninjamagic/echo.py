import esper

from ninjamagic import bus
from ninjamagic.component import Connection, Transform


def process():
    if bus.is_empty(bus.Echo):
        return

    clients = esper.get_components(Connection, Transform)
    for sig in bus.iter(bus.Echo):
        # TODO: some reaches wont care about origin
        origin = esper.try_component(sig.source, Transform)
        for eid, comps in clients:
            _, pos = comps

            if sig.source == eid and sig.text:
                bus.pulse(bus.Outbound(to=eid, text=sig.text))
                continue

            if sig.target == eid and sig.target_text:
                if sig.force_send_to_target or origin and sig.range(origin, pos):
                    bus.pulse(bus.Outbound(to=eid, text=sig.target_text))
                continue

            if sig.otext and origin and sig.range(origin, pos):
                bus.pulse(bus.Outbound(to=eid, text=sig.otext))
