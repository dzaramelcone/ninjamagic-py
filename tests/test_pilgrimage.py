# tests/test_pilgrimage.py


def test_sacrifice_component():
    """Sacrifice items track what was given."""
    from ninjamagic.component import Sacrifice, SacrificeType

    sacrifice = Sacrifice(
        sacrifice_type=SacrificeType.XP,
        amount=100.0,
        source_anchor=1,
        source_player=2,
    )

    assert sacrifice.sacrifice_type == SacrificeType.XP
    assert sacrifice.amount == 100.0
    assert sacrifice.source_anchor == 1
    assert sacrifice.source_player == 2


def test_sacrifice_strength():
    """Sacrifice strength is derived from amount."""
    from ninjamagic.component import Sacrifice, SacrificeType, get_sacrifice_strength

    small = Sacrifice(
        sacrifice_type=SacrificeType.XP, amount=50.0, source_anchor=1, source_player=1
    )
    large = Sacrifice(
        sacrifice_type=SacrificeType.XP, amount=200.0, source_anchor=1, source_player=1
    )

    assert get_sacrifice_strength(small) < get_sacrifice_strength(large)
    assert 0.0 < get_sacrifice_strength(small) <= 1.0
    assert 0.0 < get_sacrifice_strength(large) <= 1.0
