# tests/test_anchor.py
from ninjamagic.component import Anchor


def test_anchor_has_properties():
    """Anchors have strength, fuel, and eternal flag."""
    anchor = Anchor(strength=1.0, fuel=100.0, eternal=False)

    assert anchor.strength == 1.0
    assert anchor.fuel == 100.0
    assert anchor.eternal is False
    assert anchor.max_fuel == 100.0  # Derived from initial


def test_anchor_defaults():
    """Anchors have sensible defaults."""
    anchor = Anchor()

    assert anchor.strength == 1.0
    assert anchor.fuel == 100.0
    assert anchor.eternal is False


def test_eternal_anchor():
    """Eternal anchors have special properties."""
    anchor = Anchor(eternal=True)

    assert anchor.eternal is True


def test_stability_radius_full_strength():
    """Full strength anchor has maximum radius."""
    from ninjamagic.anchor import BASE_STABILITY_RADIUS, get_stability_radius

    anchor = Anchor(strength=1.0, fuel=100.0)
    radius = get_stability_radius(anchor)

    assert radius == BASE_STABILITY_RADIUS


def test_stability_radius_scales_with_strength():
    """Weaker anchors have smaller radius."""
    from ninjamagic.anchor import BASE_STABILITY_RADIUS, get_stability_radius

    weak = Anchor(strength=0.5, fuel=100.0)
    strong = Anchor(strength=1.0, fuel=100.0)

    assert get_stability_radius(weak) < get_stability_radius(strong)
    assert get_stability_radius(weak) == BASE_STABILITY_RADIUS * 0.5


def test_stability_radius_scales_with_fuel():
    """Low fuel reduces effective radius."""
    from ninjamagic.anchor import get_stability_radius

    full = Anchor(strength=1.0, fuel=100.0, max_fuel=100.0)
    half = Anchor(strength=1.0, fuel=50.0, max_fuel=100.0)
    empty = Anchor(strength=1.0, fuel=0.0, max_fuel=100.0)

    assert get_stability_radius(full) > get_stability_radius(half)
    assert get_stability_radius(half) > get_stability_radius(empty)
    assert get_stability_radius(empty) == 0.0
