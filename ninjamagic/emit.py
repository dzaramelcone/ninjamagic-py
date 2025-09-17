import esper

from ninjamagic import bus
from ninjamagic.component import Connection, Position
from ninjamagic.util import VIEWSPAN, Reach


def adjacent(this: Position, that: Position) -> bool:
    return this == that


def visible(this: Position, that: Position) -> bool:
    dx = abs(this.x - that.x)
    dy = abs(this.y - that.y)
    dz = abs(this.z - that.z)
    return max(dx, dy, dz) <= VIEWSPAN


in_range = {Reach.adjacent: adjacent, Reach.visible: visible}


def process():
    clients = esper.get_components(Connection, Position)
    for sig in bus.iter(bus.Emit):
        origin = esper.try_component(sig.source, Position)
        if not origin:  # TODO: some reaches wont care.
            continue

        pred = in_range[sig.reach]
        for eid, _, pos in clients:
            if sig.source == eid:
                continue

            if pred(origin, pos):
                bus.pulse(bus.Outbound(to=eid, text=sig.text))
