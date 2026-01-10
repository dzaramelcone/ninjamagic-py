# ninjamagic/anchor.py
"""Anchor system: stability radius, fuel, maintenance."""

from ninjamagic.component import Anchor

# Base stability radius at full strength and fuel (in cells)
BASE_STABILITY_RADIUS = 24

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
