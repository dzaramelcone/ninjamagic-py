import logging

import esper

from ninjamagic import bus
from ninjamagic.component import (
    AABB,
    Connection,
    Glyph,
    Health,
    Noun,
    Stance,
    Transform,
)
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
    sig_glyph = esper.try_component(sig.source, Glyph)
    sig_noun = esper.try_component(sig.source, Noun)
    sig_health = esper.try_component(sig.source, Health)
    sig_stance = esper.try_component(sig.source, Stance)
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
        if sig_glyph:
            bus.pulse(
                bus.OutboundGlyph(to=sig.source, source=sig.source, glyph=sig_glyph)
            )
        if sig_health:
            bus.pulse(
                bus.OutboundHealth(
                    to=sig.source,
                    source=sig.source,
                    pct=sig_health.cur / 100.0,
                    stress_pct=sig_health.stress / 200.0,
                )
            )
        if sig_noun:
            bus.pulse(
                bus.OutboundNoun(to=sig.source, source=sig.source, noun=sig_noun.value)
            )
        if sig_stance:
            bus.pulse(
                bus.OutboundStance(
                    to=sig.source, source=sig.source, stance=sig_stance.cur
                )
            )
        if not same_map:
            bus.pulse(
                bus.OutboundChipSet(
                    to=sig.source,
                    chipset=esper.component_for_entity(sig.to_map_id, ChipSet),
                )
            )

    for o_id, (o_pos, o_glyph) in esper.get_components(Transform, Glyph):
        if o_id == sig.source:
            continue

        o_noun = esper.try_component(o_id, Noun)
        o_health = esper.try_component(o_id, Health)
        o_stance = esper.try_component(o_id, Stance)

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
                ),
            )
            if sig_glyph:
                bus.pulse(
                    bus.OutboundGlyph(to=o_id, source=sig.source, glyph=sig_glyph)
                )
            if sig_health:
                bus.pulse(
                    bus.OutboundHealth(
                        to=o_id,
                        source=sig.source,
                        pct=sig_health.cur / 100.0,
                        stress_pct=sig_health.stress / 200.0,
                    )
                )
            if sig_noun:
                bus.pulse(
                    bus.OutboundNoun(to=o_id, source=sig.source, noun=sig_noun.value)
                )
            if sig_stance:
                bus.pulse(
                    bus.OutboundStance(
                        to=o_id, source=sig.source, stance=sig_stance.cur
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
            if o_glyph:
                bus.pulse(bus.OutboundGlyph(to=sig.source, source=o_id, glyph=o_glyph))
            if o_health:
                bus.pulse(
                    bus.OutboundHealth(
                        to=sig.source,
                        source=o_id,
                        pct=o_health.cur / 100.0,
                        stress_pct=o_health.stress / 200.0,
                    )
                )
            if o_noun:
                bus.pulse(
                    bus.OutboundNoun(to=sig.source, source=o_id, noun=o_noun.value)
                )
            if o_stance:
                bus.pulse(
                    bus.OutboundStance(to=sig.source, source=o_id, stance=o_stance.cur)
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
            if sig_glyph:
                bus.pulse(
                    bus.OutboundGlyph(to=o_id, source=sig.source, glyph=sig_glyph)
                )
            if sig_health:
                bus.pulse(
                    bus.OutboundHealth(
                        to=o_id,
                        source=sig.source,
                        pct=sig_health.cur / 100.0,
                        stress_pct=sig_health.stress / 200.0,
                    )
                )
            if sig_noun:
                bus.pulse(
                    bus.OutboundNoun(to=o_id, source=sig.source, noun=sig_noun.value)
                )
            if sig_stance:
                bus.pulse(
                    bus.OutboundStance(
                        to=o_id, source=sig.source, stance=sig_stance.cur
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
