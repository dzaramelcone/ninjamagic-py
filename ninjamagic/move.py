import esper

from ninjamagic import bus
from ninjamagic.component import (
    Connection,
    Location,
    Slot,
    Transform,
    transform,
)
from ninjamagic.world.state import can_enter


def process():
    for sig in bus.iter(bus.MovePosition):
        loc = transform(sig.source)
        bus.pulse(
            bus.PositionChanged(
                source=sig.source,
                from_map_id=loc.map_id,
                from_y=loc.y,
                from_x=loc.x,
                to_map_id=sig.to_map_id,
                to_y=sig.to_y,
                to_x=sig.to_x,
                quiet=sig.quiet,
            )
        )
        if esper.has_component(sig.source, Location):
            esper.add_component(sig.source, sig.to_map_id, Location)
        if esper.has_component(sig.source, Slot):
            esper.add_component(sig.source, Slot.UNSET)

    for sig in bus.iter(bus.MoveCompass):
        loc = transform(sig.source)

        delta_y, delta_x = sig.dir.to_vector()
        to_y, to_x = (loc.y + delta_y), (loc.x + delta_x)

        if not can_enter(map_id=loc.map_id, y=to_y, x=to_x):
            if esper.has_component(sig.source, Connection):
                bus.pulse(bus.Outbound(to=sig.source, text="You can't go there."))
            continue

        bus.pulse(
            bus.PositionChanged(
                source=sig.source,
                from_map_id=loc.map_id,
                from_x=loc.x,
                from_y=loc.y,
                to_map_id=loc.map_id,
                to_x=to_x,
                to_y=to_y,
            )
        )

    for sig in bus.iter(bus.MoveEntity):
        esper.add_component(sig.source, sig.container, Location)
        esper.add_component(sig.source, sig.slot)

        if esper.has_component(sig.source, Transform):
            loc = transform(sig.source)
            bus.pulse(
                bus.PositionChanged(
                    source=sig.source,
                    from_map_id=loc.map_id,
                    from_y=loc.y,
                    from_x=loc.x,
                    to_map_id=0,
                    to_y=0,
                    to_x=0,
                    quiet=True,
                )
            )

    # mutate
    for sig in bus.iter(bus.PositionChanged):
        loc = transform(sig.source)
        loc.map_id, loc.y, loc.x = sig.to_map_id, sig.to_y, sig.to_x
