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


def test_pilgrimage_state():
    """Players in pilgrimage have special state."""
    from ninjamagic.component import PilgrimageState

    state = PilgrimageState(
        sacrifice_entity=123,
        start_time=1000.0,
        stress_rate_multiplier=3.0,
        damage_taken_multiplier=1.5,
    )

    assert state.sacrifice_entity == 123
    assert state.start_time == 1000.0
    assert state.stress_rate_multiplier == 3.0
    assert state.damage_taken_multiplier == 1.5


def test_sacrifice_creates_item():
    """Sacrifice command creates a sacrifice item and enters pilgrimage."""
    import esper

    from ninjamagic.component import (
        Anchor,
        Health,
        PilgrimageState,
        Sacrifice,
        SacrificeType,
        Skills,
        Transform,
    )
    from ninjamagic.pilgrimage import make_sacrifice

    esper.clear_database()

    map_id = esper.create_entity()

    # Create an anchor
    anchor = esper.create_entity()
    esper.add_component(anchor, Transform(map_id=map_id, y=10, x=10))
    esper.add_component(anchor, Anchor())

    # Create a player near the anchor
    player = esper.create_entity()
    esper.add_component(player, Transform(map_id=map_id, y=10, x=11))
    esper.add_component(player, Health(cur=100.0))
    esper.add_component(player, Skills())

    # Make sacrifice
    result = make_sacrifice(
        player_eid=player,
        sacrifice_type=SacrificeType.XP,
        amount=100.0,
        now=1000.0,
    )

    assert result is not None
    sacrifice_eid = result

    # Player should now be in pilgrimage state
    assert esper.has_component(player, PilgrimageState)

    # Sacrifice item should exist
    assert esper.has_component(sacrifice_eid, Sacrifice)
    sacrifice = esper.component_for_entity(sacrifice_eid, Sacrifice)
    assert sacrifice.amount == 100.0
    assert sacrifice.source_player == player
