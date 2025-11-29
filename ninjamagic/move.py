import esper

from ninjamagic import bus
from ninjamagic.component import Connection, transform
from ninjamagic.world.state import can_enter


def process():
    for sig in bus.iter(bus.MoveCompass):
        loc = transform(sig.source)

        from_map_id = loc.map_id
        from_y, from_x = loc.y, loc.x

        delta_y, delta_x = sig.dir.to_vector()
        to_y, to_x = (from_y + delta_y), (from_x + delta_x)
        to_map_id = from_map_id

        if not can_enter(map_id=loc.map_id, y=to_y, x=to_x):
            if esper.has_component(sig.source, Connection):
                bus.pulse(bus.Outbound(to=sig.source, text="You can't go there."))
            continue

        bus.pulse(
            bus.PositionChanged(
                source=sig.source,
                from_map_id=from_map_id,
                from_x=from_x,
                from_y=from_y,
                to_map_id=to_map_id,
                to_x=to_x,
                to_y=to_y,
            )
        )

    # mutate
    for sig in bus.iter(bus.PositionChanged):
        loc = transform(sig.source)
        loc.map_id, loc.y, loc.x = sig.to_map_id, sig.to_y, sig.to_x
