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

            if sig.source == eid and sig.make_source_sig:
                bus.pulse(sig.make_source_sig(to=eid))
                continue

            if sig.target == eid and sig.make_target_sig:
                if sig.force_send_to_target or origin and sig.reach(origin, pos):
                    bus.pulse(sig.make_target_sig(to=eid))
                continue

            if sig.make_other_sig and origin and sig.reach(origin, pos):
                bus.pulse(sig.make_other_sig(to=eid))
