# tests/test_anchor.py
import pytest
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
