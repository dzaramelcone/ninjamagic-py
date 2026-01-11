# ninjamagic/anchor.py
"""Anchor system: stability radius, fuel, maintenance."""

import esper

from ninjamagic import bus
from ninjamagic.component import Anchor

# Base stability radius at full strength and fuel (in cells)
BASE_STABILITY_RADIUS = 24

# Fuel consumed per second (100 fuel = ~16 minutes at base rate)
FUEL_CONSUMPTION_RATE = 0.1

# Minimum radius (below this, anchor provides no protection)
MIN_STABILITY_RADIUS = 4


def get_stability_radius(anchor: Anchor) -> float:
    """Calculate the stability radius for an anchor.

    Radius = BASE * strength * fuel_fraction
    Returns 0.0 if fuel is empty (anchor is out).
    """
    if anchor.fuel <= 0 and not anchor.eternal:
        return 0.0

    fuel_fraction = anchor.fuel / anchor.max_fuel if anchor.max_fuel > 0 else 1.0

    # Eternal anchors always have full fuel effect
    if anchor.eternal:
        fuel_fraction = 1.0

    radius = BASE_STABILITY_RADIUS * anchor.strength * fuel_fraction

    # If below minimum, return 0 (effectively dead)
    if radius < MIN_STABILITY_RADIUS and not anchor.eternal:
        return 0.0

    return radius


def consume_fuel(anchor: Anchor, *, seconds: float) -> None:
    """Consume fuel from an anchor over time.

    Does nothing for eternal anchors.
    """
    if anchor.eternal:
        return

    consumption = FUEL_CONSUMPTION_RATE * seconds
    anchor.fuel = max(0.0, anchor.fuel - consumption)


def add_fuel(anchor: Anchor, *, amount: float) -> float:
    """Add fuel to an anchor.

    Returns the amount actually added (may be less if near max).
    """
    old_fuel = anchor.fuel
    anchor.fuel = min(anchor.max_fuel, anchor.fuel + amount)
    return anchor.fuel - old_fuel


def get_anchor_positions_with_radii() -> list[tuple[int, int, float]]:
    """Get all anchor positions with their stability radii.

    Returns list of (y, x, radius) tuples.
    """
    from ninjamagic.component import Transform

    result = []

    for _eid, (anchor, transform) in esper.get_components(Anchor, Transform):
        radius = get_stability_radius(anchor)
        if radius > 0:
            result.append((transform.y, transform.x, radius))

    return result


def process(*, delta_seconds: float) -> None:
    """Process all anchors: consume fuel, handle tending signals."""

    # Handle tending signals
    for sig in bus.iter(bus.TendAnchor):
        if esper.has_component(sig.anchor, Anchor):
            anchor = esper.component_for_entity(sig.anchor, Anchor)
            add_fuel(anchor, amount=sig.fuel_amount)

    # Consume fuel from all anchors
    for _eid, anchor in esper.get_component(Anchor):
        consume_fuel(anchor, seconds=delta_seconds)
