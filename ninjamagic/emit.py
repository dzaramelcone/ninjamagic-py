import esper

from ninjamagic import bus
from ninjamagic.component import Connection, Position
from ninjamagic.util import VIEW_STRIDE, Reach


def adjacent(this: Position, that: Position) -> bool:
    return this == that


def visible(this: Position, that: Position) -> bool:
    return (
        abs(this.x - that.x) <= VIEW_STRIDE.width
        and abs(this.y - that.y) <= VIEW_STRIDE.height
    )


in_range = {Reach.adjacent: adjacent, Reach.visible: visible}


def process():
    if bus.empty(bus.Emit):
        return

    clients = esper.get_components(Connection, Position)
    for sig in bus.iter(bus.Emit):
        origin = esper.try_component(sig.source, Position)
        if not origin:  # TODO: some reaches wont care.
            continue

        pred = in_range[sig.reach]
        for eid, comps in clients:
            _, pos = comps
            if sig.source == eid:
                continue

            if pred(origin, pos):
                bus.pulse(bus.Outbound(to=eid, text=sig.text))
