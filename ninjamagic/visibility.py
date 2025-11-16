import logging

import esper

from ninjamagic import bus
from ninjamagic.component import AABB, Connection, Glyph, Transform
from ninjamagic.util import VIEW_STRIDE
from ninjamagic.world.state import ChipSet

log = logging.getLogger(__name__)
VIEW_H, VIEW_W = VIEW_STRIDE
CORNERS = (
    (VIEW_H, VIEW_W),
    (-VIEW_H, VIEW_W),
    (VIEW_H, -VIEW_W),
    (-VIEW_H, -VIEW_W),
)


def notify_movement(sig: bus.PositionChanged):
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
                    to=sig.source,
                    chipset=esper.component_for_entity(sig.to_map_id, ChipSet),
                )
            )

    for o_id, (o_pos, _) in esper.get_components(Transform, Glyph):
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


def notify_gas(sig: bus.GasUpdated):
    # TODO optimize lol
    # possible we just send gas create events over net and let client render.
    # but if terrain changes or it reaches out of view places, it could desync.

    for eid, (transform, _) in esper.get_components(Transform, Connection):
        if sig.transform.map_id != transform.map_id:
            continue
        if not sig.aabb.intersects(
            other=AABB(
                top=transform.y - VIEW_H,
                bot=transform.y + VIEW_H,
                left=transform.x - VIEW_W,
                right=transform.x + VIEW_W,
            )
        ):
            continue
        for (y, x), v in sig.gas.items():
            if abs(transform.y - y) > VIEW_H or abs(transform.x - x) > VIEW_W:
                continue
            bus.pulse(
                bus.OutboundGas(
                    to=eid,
                    gas_id=sig.source,
                    map_id=sig.transform.map_id,
                    x=x,
                    y=y,
                    v=v,
                )
            )


def process():
    for sig in bus.iter(bus.PositionChanged):
        notify_movement(sig)

    for sig in bus.iter(bus.GasUpdated):
        notify_gas(sig)
