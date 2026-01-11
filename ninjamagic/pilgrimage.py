"""Pilgrimage system: sacrifice, journey, and anchor creation."""

import esper

from ninjamagic.component import (
    Anchor,
    Glyph,
    Health,
    Noun,
    PilgrimageState,
    Pronouns,
    Sacrifice,
    SacrificeType,
    Transform,
)


def _find_nearby_anchor(map_id: int, y: int, x: int, max_distance: int = 2) -> int | None:
    """Find an anchor within range of the position."""
    for eid, (_anchor, transform) in esper.get_components(Anchor, Transform):
        if transform.map_id != map_id:
            continue
        if abs(transform.y - y) <= max_distance and abs(transform.x - x) <= max_distance:
            return eid
    return None


def make_sacrifice(
    *,
    player_eid: int,
    sacrifice_type: SacrificeType,
    amount: float,
    now: float,
) -> int | None:
    """Make a sacrifice at a nearby anchor.

    Returns the sacrifice entity ID, or None if failed.
    """
    # Must be near an anchor
    transform = esper.component_for_entity(player_eid, Transform)
    anchor_eid = _find_nearby_anchor(transform.map_id, transform.y, transform.x)

    if anchor_eid is None:
        return None

    # Must not already be on pilgrimage
    if esper.has_component(player_eid, PilgrimageState):
        return None

    # Validate and apply cost
    if sacrifice_type == SacrificeType.HEALTH:
        health = esper.component_for_entity(player_eid, Health)
        if health.cur < amount:
            return None
        health.cur -= amount

    # Create sacrifice item
    sacrifice_eid = esper.create_entity()
    esper.add_component(
        sacrifice_eid,
        Sacrifice(
            sacrifice_type=sacrifice_type,
            amount=amount,
            source_anchor=anchor_eid,
            source_player=player_eid,
        ),
    )
    esper.add_component(sacrifice_eid, Noun(value="sacrifice", pronoun=Pronouns.IT))
    esper.add_component(sacrifice_eid, ("✧", 0.15, 0.8, 0.9), Glyph)

    # Put player in pilgrimage state
    esper.add_component(
        player_eid,
        PilgrimageState(
            sacrifice_entity=sacrifice_eid,
            start_time=now,
        ),
    )

    return sacrifice_eid


def cancel_pilgrimage(player_eid: int) -> None:
    """Cancel a pilgrimage (e.g., on death)."""
    if not esper.has_component(player_eid, PilgrimageState):
        return

    state = esper.component_for_entity(player_eid, PilgrimageState)

    # Destroy sacrifice
    if esper.entity_exists(state.sacrifice_entity):
        esper.delete_entity(state.sacrifice_entity)

    # Remove pilgrimage state
    esper.remove_component(player_eid, PilgrimageState)


def get_damage_multiplier(player_eid: int) -> float:
    """Get the damage multiplier for a player (higher = takes more damage)."""
    if not esper.has_component(player_eid, PilgrimageState):
        return 1.0
    state = esper.component_for_entity(player_eid, PilgrimageState)
    return state.damage_taken_multiplier


def get_stress_multiplier(player_eid: int) -> float:
    """Get the stress rate multiplier for a player."""
    if not esper.has_component(player_eid, PilgrimageState):
        return 1.0
    state = esper.component_for_entity(player_eid, PilgrimageState)
    return state.stress_rate_multiplier
