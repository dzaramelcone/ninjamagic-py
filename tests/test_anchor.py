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


def test_fuel_consumption():
    """Anchors consume fuel over time."""
    from ninjamagic.anchor import FUEL_CONSUMPTION_RATE, consume_fuel

    anchor = Anchor(strength=1.0, fuel=100.0, max_fuel=100.0)

    # Consume fuel for 1 second
    consume_fuel(anchor, seconds=1.0)

    assert anchor.fuel == 100.0 - FUEL_CONSUMPTION_RATE


def test_fuel_consumption_stops_at_zero():
    """Fuel doesn't go negative."""
    from ninjamagic.anchor import consume_fuel

    anchor = Anchor(strength=1.0, fuel=1.0, max_fuel=100.0)

    # Consume more than available
    consume_fuel(anchor, seconds=1000.0)

    assert anchor.fuel == 0.0


def test_eternal_anchor_no_consumption():
    """Eternal anchors don't consume fuel."""
    from ninjamagic.anchor import consume_fuel

    anchor = Anchor(strength=1.0, fuel=100.0, eternal=True)

    consume_fuel(anchor, seconds=1000.0)

    assert anchor.fuel == 100.0


def test_add_fuel():
    """Players can add fuel to anchors."""
    from ninjamagic.anchor import add_fuel

    anchor = Anchor(strength=1.0, fuel=50.0, max_fuel=100.0)

    add_fuel(anchor, amount=25.0)

    assert anchor.fuel == 75.0


def test_add_fuel_caps_at_max():
    """Fuel can't exceed max_fuel."""
    from ninjamagic.anchor import add_fuel

    anchor = Anchor(strength=1.0, fuel=90.0, max_fuel=100.0)

    add_fuel(anchor, amount=50.0)

    assert anchor.fuel == 100.0


def test_anchor_processor():
    """Anchor processor consumes fuel and handles tending."""
    import esper

    from ninjamagic import bus
    from ninjamagic.anchor import process
    from ninjamagic.component import Anchor, Transform

    esper.clear_database()

    # Create an anchor
    anchor_eid = esper.create_entity()
    esper.add_component(anchor_eid, Anchor(strength=1.0, fuel=100.0, max_fuel=100.0))
    esper.add_component(anchor_eid, Transform(map_id=1, y=0, x=0))

    # Process for 10 seconds
    process(delta_seconds=10.0)
    bus.clear()

    anchor = esper.component_for_entity(anchor_eid, Anchor)
    assert anchor.fuel < 100.0  # Fuel consumed
