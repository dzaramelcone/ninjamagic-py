"""Anchor system: stability radius, growth, and defense.

Anchors are bonfires that provide protection from the darkness.
- They protect tiles within their threshold from decay
- They contest against wave mobs that attack them
- They contest against local hostility each night
- Players resting at anchors can grow the anchor's rank
"""

import logging

import esper

from ninjamagic import bus
from ninjamagic.component import (
    Anchor,
    Connection,
    EntityId,
    Health,
    Hostility,
    Skills,
    Stance,
    Transform,
)
from ninjamagic.util import Trial, contest, tags

log = logging.getLogger(__name__)


def anchor_protects(anchor: Anchor, transform: Transform, y: int, x: int) -> bool:
    """Check if an anchor protects a tile at (y, x)."""
    return abs(transform.y - y) + abs(transform.x - x) < anchor.threshold


def any_anchor_protects(map_id: EntityId, y: int, x: int) -> bool:
    """Check if any anchor protects a tile at (y, x) on the given map."""
    for _, (anchor, transform) in esper.get_components(Anchor, Transform):
        if transform.map_id == map_id and anchor_protects(anchor, transform, y, x):
            return True
    return False


def find_anchor_at(map_id: EntityId, y: int, x: int) -> EntityId | None:
    """Find an anchor entity at the exact (y, x) position."""
    for eid, (_, transform) in esper.get_components(Anchor, Transform):
        if transform.map_id == map_id and transform.y == y and transform.x == x:
            return eid
    return None


def grow_anchor(anchor_eid: EntityId, *, player_rank: int) -> bool:
    """Try to grow an anchor's rank based on player skill.

    Returns True if the anchor grew.
    """
    anchor = esper.component_for_entity(anchor_eid, Anchor)

    # Contest player rank against current anchor rank (harder to grow stronger anchors)
    mult = contest(player_rank, anchor.rank, tag="anchor_growth")
    if Trial.check(mult=mult, difficulty=Trial.SOMEWHAT_HARD):
        anchor.rank += 1
        log.info(
            "anchor_growth: %s",
            tags(
                anchor=anchor_eid,
                old_rank=anchor.rank - 1,
                new_rank=anchor.rank,
                player_rank=player_rank,
                mult=mult,
            ),
        )
        return True
    return False


def wave_mob_attacks_anchor(anchor_eid: EntityId, *, mob_strength: int) -> bool:
    """Wave mob contests against anchor. Anchor loses 1 rank if it loses.

    Returns True if the anchor was damaged (lost rank).
    Returns False if the anchor defended successfully.
    """
    anchor = esper.component_for_entity(anchor_eid, Anchor)

    # Mob strength vs anchor rank
    mult = contest(mob_strength, anchor.rank, tag="wave_mob_vs_anchor")

    if Trial.check(mult=mult):
        # Mob wins - anchor loses a rank
        old_rank = anchor.rank
        anchor.rank -= 1

        log.info(
            "anchor_damaged: %s",
            tags(
                anchor=anchor_eid,
                old_rank=old_rank,
                new_rank=anchor.rank,
                mob_strength=mob_strength,
                mult=mult,
            ),
        )

        # Check if anchor is destroyed
        if anchor.rank <= 0:
            bus.pulse(bus.AnchorDestroyed(anchor=anchor_eid))

        return True

    log.info(
        "anchor_defended: %s",
        tags(
            anchor=anchor_eid,
            rank=anchor.rank,
            mob_strength=mob_strength,
            mult=mult,
        ),
    )
    return False


def anchor_contests_hostility(anchor_eid: EntityId) -> bool:
    """End-of-night contest: anchor rank vs local hostility.

    Returns True if the anchor survives.
    Returns False if the anchor is destroyed.
    """
    anchor = esper.component_for_entity(anchor_eid, Anchor)
    transform = esper.component_for_entity(anchor_eid, Transform)

    # Get local hostility
    hostility_component = esper.try_component(transform.map_id, Hostility)
    if not hostility_component:
        # No hostility = anchor survives
        return True

    local_hostility = hostility_component.at(transform.y, transform.x)

    # Anchor rank vs hostility
    mult = contest(anchor.rank, local_hostility, tag="anchor_vs_hostility")

    if not Trial.check(mult=mult):
        # Anchor loses - destroyed by the darkness
        log.info(
            "anchor_consumed: %s",
            tags(
                anchor=anchor_eid,
                rank=anchor.rank,
                hostility=local_hostility,
                mult=mult,
            ),
        )
        bus.pulse(bus.AnchorDestroyed(anchor=anchor_eid))
        return False

    log.info(
        "anchor_persists: %s",
        tags(
            anchor=anchor_eid,
            rank=anchor.rank,
            hostility=local_hostility,
            mult=mult,
        ),
    )
    return True


def process_rest_growth() -> None:
    """Process anchor growth from players resting at anchors.

    Called during RestCheck processing. Players must be at the same tile
    as an anchor to grow it.
    """
    for _eid, cmps in esper.get_components(Connection, Transform, Health, Stance, Skills):
        _, loc, health, stance, skills = cmps

        if health.condition != "normal":
            continue

        if not stance.camping():
            continue

        # Check if player is at an anchor
        anchor_eid = find_anchor_at(loc.map_id, loc.y, loc.x)
        if not anchor_eid:
            continue

        # Player's highest skill determines growth potential
        survival_rank = skills.survival.rank
        if grow_anchor(anchor_eid, player_rank=survival_rank):
            # Could emit a signal/story here for feedback
            pass


def process_end_of_night_contests() -> None:
    """Process end-of-night contests for all anchors.

    Anchors contest against local hostility. Those that lose are destroyed.
    """
    # Collect anchors to process (avoid modifying while iterating)
    anchors_to_check = [eid for eid, _ in esper.get_components(Anchor, Transform)]

    for anchor_eid in anchors_to_check:
        if not esper.entity_exists(anchor_eid):
            continue
        anchor_contests_hostility(anchor_eid)


def process() -> None:
    """Process anchor signals."""
    # Handle anchor destruction
    for sig in bus.iter(bus.AnchorDestroyed):
        if esper.entity_exists(sig.anchor):
            esper.delete_entity(sig.anchor)

    # Handle wave mob attacks on anchors
    for sig in bus.iter(bus.WaveMobAttacksAnchor):
        if esper.entity_exists(sig.anchor):
            wave_mob_attacks_anchor(sig.anchor, mob_strength=sig.mob_strength)

    # Handle RestCheck - anchor growth and end-of-night contests
    if not bus.is_empty(bus.RestCheck):
        process_rest_growth()
        process_end_of_night_contests()
