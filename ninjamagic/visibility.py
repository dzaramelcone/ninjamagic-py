import logging
import esper
from typing import Callable, Generator
from ninjamagic import bus
from ninjamagic.component import Connection, EntityId, Name, Transform, transform
from ninjamagic.util import VIEW_STRIDE
from ninjamagic.world import get_chipset

log = logging.getLogger(__name__)
Reach = Callable[[Transform, Transform], bool]
VIEW_W, VIEW_H = VIEW_STRIDE.width, VIEW_STRIDE.height
CORNERS = (
    (VIEW_W, VIEW_H),
    (-VIEW_W, VIEW_H),
    (VIEW_W, -VIEW_H),
    (-VIEW_W, -VIEW_H),
)


def adjacent(this: Transform, that: Transform) -> bool:
    # symmetric, transitive, reflexive
    return this == that


def visible(this: Transform, that: Transform) -> bool:
    # symmetric, intransitive, reflexive
    return (
        this.map_id == that.map_id
        and abs(this.x - that.x) <= VIEW_STRIDE.width
        and abs(this.y - that.y) <= VIEW_STRIDE.height
    )


def find(
    this: EntityId, prefix: str, reach: Reach
) -> Generator[tuple[EntityId, Name, Transform], None, None]:
    u_tfm = transform(this)
    for o_id, (name, o_tfm) in esper.get_component(Name, Transform):
        if o_id == this:
            continue
        if not name.startswith(prefix):
            continue
        if not reach(o_tfm, u_tfm):
            continue
        yield o_id, name, o_tfm


def process():
    for sig in bus.iter(bus.PositionChanged):
        notify_source = esper.has_component(sig.source, Connection)
        same_map = sig.to_map_id == sig.from_map_id
        # tell source. send tiles.
        if notify_source:
            bus.pulse(
                bus.OutboundMove(
                    to=sig.source,
                    source=sig.source,
                    map_id=sig.to_map_id,
                    x=sig.to_x,
                    y=sig.to_y,
                ),
                *[
                    bus.OutboundTile(
                        to=sig.source,
                        map_id=sig.to_map_id,
                        top=sig.to_y + dy,
                        left=sig.to_x + dx,
                    )
                    for dx, dy in CORNERS
                ],
            )
            if not same_map:
                bus.pulse(
                    bus.OutboundChipSet(
                        to=sig.source, chipset=get_chipset(map_id=sig.to_map_id)
                    )
                )

        for o_id, o_pos in esper.get_component(Transform):
            if o_id == sig.source:
                continue

            notify_other = esper.has_component(o_id, Connection)

            # in-range checks
            in_to = (
                o_pos.map_id == sig.to_map_id
                and abs(o_pos.x - sig.to_x) <= VIEW_W
                and abs(o_pos.y - sig.to_y) <= VIEW_H
            )

            in_from = (
                o_pos.map_id == sig.from_map_id
                and abs(o_pos.x - sig.from_x) <= VIEW_W
                and abs(o_pos.y - sig.from_y) <= VIEW_H
            )

            # publish to new observers
            if notify_other and in_to:
                bus.pulse(
                    bus.OutboundMove(
                        to=o_id,
                        source=sig.source,
                        map_id=sig.to_map_id,
                        x=sig.to_x,
                        y=sig.to_y,
                    )
                )

            # symmetrical
            if notify_source and in_to:
                bus.pulse(
                    bus.OutboundMove(
                        to=sig.source,
                        source=o_id,
                        map_id=o_pos.map_id,
                        x=o_pos.x,
                        y=o_pos.y,
                    )
                )

            # publish to former observers
            if notify_other and in_from and not in_to:
                bus.pulse(
                    bus.OutboundMove(
                        to=o_id,
                        source=sig.source,
                        map_id=sig.to_map_id,
                        x=sig.to_x,
                        y=sig.to_y,
                    )
                )
