"""Demon power system - Q2 full implementation, Q1 preview for pilgrimage."""

from dataclasses import dataclass

import esper

from ninjamagic.component import PilgrimageState


@dataclass(frozen=True)
class DemonPower:
    """A demon power with upside and downside."""

    name: str
    description: str
    upside: str
    downside: str


# Preview power for pilgrimage state
PILGRIMAGE_POWER = DemonPower(
    name="Dark Vigor",
    description="The demon sustains you through the darkness.",
    upside="Passive health regeneration",
    downside="Constant hunger drain",
)


def get_active_demon_power(player_eid: int) -> DemonPower | None:
    """Get the active demon power for a player, if any.

    In Q1, only players on pilgrimage have a power.
    In Q2, stress thresholds will also grant powers.
    """
    if not esper.has_component(player_eid, PilgrimageState):
        return None

    return PILGRIMAGE_POWER


def process_demon_effects(*, delta_seconds: float) -> None:
    """Process ongoing demon power effects.

    Currently only handles Dark Vigor (pilgrimage power).
    """
    from ninjamagic.component import Health

    regen_per_second = 2.0

    for eid, (_state,) in esper.get_components(PilgrimageState):
        # Dark Vigor: health regen
        if esper.has_component(eid, Health):
            health = esper.component_for_entity(eid, Health)
            health.cur = min(100.0, health.cur + regen_per_second * delta_seconds)
