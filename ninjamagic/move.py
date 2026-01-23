import esper

from ninjamagic import bus, reach
from ninjamagic.component import (
    Behavior,
    Connection,
    ContainedBy,
    Den,
    FromDen,
    Glyph,
    Slot,
    Transform,
    transform,
)
from ninjamagic.util import get_looptime
from ninjamagic.world.state import can_enter, create_mob


def process():
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
        # Wake nearby dens before position change so mobs exist for visibility
        if not esper.has_component(sig.source, Connection):
            continue
        for _, (den, tf) in esper.get_components(Den, Transform):
            if not reach.chebyshev(
                den.wake_distance,
                den.wake_distance,
                loc.map_id,
                to_y,
                to_x,
                tf.map_id,
                tf.y,
                tf.x,
            ):
                continue
            for slot in den.slots:
                if slot.is_ready(den.respawn_delay):
                    slot.mob_eid = create_mob(
                        map_id=slot.map_id,
                        y=slot.y,
                        x=slot.x,
                        name="goblin",
                        glyph=Glyph(char="g", h=0.25, s=0.7, v=0.6),
                        components=(
                            Behavior(),
                            FromDen(slot=slot),
                        ),
                    )
                    slot.spawn_time = get_looptime()
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
        if esper.has_component(sig.source, ContainedBy):
            esper.add_component(sig.source, 0, ContainedBy)
        if esper.has_component(sig.source, Slot):
            esper.add_component(sig.source, Slot.ANY)

    for sig in bus.iter(bus.MoveEntity):
        esper.add_component(sig.source, sig.container, ContainedBy)
        esper.add_component(sig.source, sig.slot)

        if loc := esper.try_component(sig.source, Transform):
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
