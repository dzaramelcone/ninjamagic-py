"""Tests for wyrd system: sacrifice decision tree, enter/exit wyrd state."""

from unittest.mock import patch

import esper
import pytest

from ninjamagic import bus
from ninjamagic.component import (
    Anchor,
    Anima,
    Connection,
    DamageTakenMultiplier,
    Glyph,
    Health,
    LastRestGains,
    Noun,
    ProcBonus,
    Pronouns,
    Stats,
    StatSickness,
    Transform,
    Wyrd,
)
from ninjamagic.wyrd import (
    create_anima,
    enter_wyrd_state,
    exit_wyrd_state,
    get_highest_stat,
    get_stat_prompt,
    on_stat_sacrifice_err,
    on_stat_sacrifice_ok,
    on_xp_sacrifice_err,
    on_xp_sacrifice_ok,
    process,
    start_wyrd_prompt,
)


class MockWebSocket:
    """Stub for Connection component in tests."""

    pass


@pytest.fixture(autouse=True)
def clear_esper():
    """Clear esper database before each test."""
    esper.clear_database()
    bus.clear()
    yield
    esper.clear_database()
    bus.clear()


def create_player(map_id: int, y: int, x: int) -> int:
    """Helper to create a player entity."""
    player_eid = esper.create_entity()
    esper.add_component(player_eid, MockWebSocket(), Connection)
    esper.add_component(player_eid, Transform(map_id=map_id, y=y, x=x))
    esper.add_component(player_eid, Health(cur=100.0))
    esper.add_component(player_eid, Stats(grace=10, grit=5, wit=3))
    return player_eid


def create_anchor(map_id: int, y: int, x: int, rank: int = 5) -> int:
    """Helper to create an anchor entity."""
    anchor_eid = esper.create_entity()
    esper.add_component(anchor_eid, Anchor(rank=rank))
    esper.add_component(anchor_eid, Transform(map_id=map_id, y=y, x=x))
    return anchor_eid


class TestGetHighestStat:
    """Tests for get_highest_stat."""

    def test_grace_highest(self):
        player_eid = esper.create_entity()
        esper.add_component(player_eid, Stats(grace=10, grit=5, wit=3))
        assert get_highest_stat(player_eid) == "grace"

    def test_grit_highest(self):
        player_eid = esper.create_entity()
        esper.add_component(player_eid, Stats(grace=3, grit=10, wit=5))
        assert get_highest_stat(player_eid) == "grit"

    def test_wit_highest(self):
        player_eid = esper.create_entity()
        esper.add_component(player_eid, Stats(grace=3, grit=5, wit=10))
        assert get_highest_stat(player_eid) == "wit"


class TestGetStatPrompt:
    """Tests for get_stat_prompt."""

    def test_grace_prompt(self):
        assert get_stat_prompt("grace") == "catch the falling ash"

    def test_grit_prompt(self):
        assert get_stat_prompt("grit") == "hold the coal"

    def test_wit_prompt(self):
        assert get_stat_prompt("wit") == "name the flame"


class TestCreateAnima:
    """Tests for create_anima."""

    def test_creates_anima_entity(self):
        map_id = esper.create_entity()
        player_eid = create_player(map_id, 10, 10)
        anchor_eid = create_anchor(map_id, 10, 10)

        anima_eid = create_anima(player_eid, anchor_eid, stat="grace", rank=5)

        assert esper.entity_exists(anima_eid)
        assert esper.has_component(anima_eid, Anima)
        assert esper.has_component(anima_eid, Noun)
        assert esper.has_component(anima_eid, Glyph)

    def test_anima_has_correct_data(self):
        map_id = esper.create_entity()
        player_eid = create_player(map_id, 10, 10)
        anchor_eid = create_anchor(map_id, 10, 10)

        anima_eid = create_anima(player_eid, anchor_eid, stat="grit", skill="survival", rank=3)

        anima = esper.component_for_entity(anima_eid, Anima)
        assert anima.source_anchor == anchor_eid
        assert anima.source_player == player_eid
        assert anima.stat == "grit"
        assert anima.skill == "survival"
        assert anima.rank == 3


class TestEnterWyrdState:
    """Tests for enter_wyrd_state."""

    def test_adds_wyrd_component(self):
        map_id = esper.create_entity()
        player_eid = create_player(map_id, 10, 10)
        anchor_eid = create_anchor(map_id, 10, 10)

        with patch("ninjamagic.wyrd.grow_anchor"):
            enter_wyrd_state(player_eid, anchor_eid)

        assert esper.has_component(player_eid, Wyrd)

    def test_adds_damage_multiplier(self):
        map_id = esper.create_entity()
        player_eid = create_player(map_id, 10, 10)
        anchor_eid = create_anchor(map_id, 10, 10)

        with patch("ninjamagic.wyrd.grow_anchor"):
            enter_wyrd_state(player_eid, anchor_eid)

        assert esper.has_component(player_eid, DamageTakenMultiplier)
        mult = esper.component_for_entity(player_eid, DamageTakenMultiplier)
        assert mult.value == 2.0

    def test_adds_proc_bonus(self):
        map_id = esper.create_entity()
        player_eid = create_player(map_id, 10, 10)
        anchor_eid = create_anchor(map_id, 10, 10)

        with patch("ninjamagic.wyrd.grow_anchor"):
            enter_wyrd_state(player_eid, anchor_eid)

        assert esper.has_component(player_eid, ProcBonus)

    def test_stat_sacrifice_adds_stat_sickness(self):
        map_id = esper.create_entity()
        player_eid = create_player(map_id, 10, 10)
        anchor_eid = create_anchor(map_id, 10, 10)

        with patch("ninjamagic.wyrd.grow_anchor"):
            enter_wyrd_state(player_eid, anchor_eid, stat="grace")

        assert esper.has_component(player_eid, StatSickness)
        sickness = esper.component_for_entity(player_eid, StatSickness)
        assert sickness.stat == "grace"
        assert sickness.nights_remaining == 3

    def test_xp_sacrifice_no_stat_sickness(self):
        map_id = esper.create_entity()
        player_eid = create_player(map_id, 10, 10)
        anchor_eid = create_anchor(map_id, 10, 10)

        with patch("ninjamagic.wyrd.grow_anchor"):
            enter_wyrd_state(player_eid, anchor_eid, skill="survival", rank=5)

        assert not esper.has_component(player_eid, StatSickness)

    def test_grows_anchor(self):
        map_id = esper.create_entity()
        player_eid = create_player(map_id, 10, 10)
        anchor_eid = create_anchor(map_id, 10, 10, rank=1)

        with patch("ninjamagic.anchor.Trial.check", return_value=True):
            enter_wyrd_state(player_eid, anchor_eid, rank=10)

        anchor = esper.component_for_entity(anchor_eid, Anchor)
        assert anchor.rank == 2  # Grew from 1 to 2


class TestExitWyrdState:
    """Tests for exit_wyrd_state."""

    def test_removes_wyrd_component(self):
        map_id = esper.create_entity()
        player_eid = create_player(map_id, 10, 10)
        anchor_eid = create_anchor(map_id, 10, 10)

        with patch("ninjamagic.wyrd.grow_anchor"):
            enter_wyrd_state(player_eid, anchor_eid)

        exit_wyrd_state(player_eid)

        assert not esper.has_component(player_eid, Wyrd)

    def test_removes_added_components(self):
        map_id = esper.create_entity()
        player_eid = create_player(map_id, 10, 10)
        anchor_eid = create_anchor(map_id, 10, 10)

        with patch("ninjamagic.wyrd.grow_anchor"):
            enter_wyrd_state(player_eid, anchor_eid, stat="grace")

        exit_wyrd_state(player_eid)

        assert not esper.has_component(player_eid, DamageTakenMultiplier)
        assert not esper.has_component(player_eid, ProcBonus)
        assert not esper.has_component(player_eid, StatSickness)

    def test_noop_if_not_wyrd(self):
        map_id = esper.create_entity()
        player_eid = create_player(map_id, 10, 10)

        # Should not raise
        exit_wyrd_state(player_eid)


class TestStartWyrdPrompt:
    """Tests for start_wyrd_prompt."""

    def test_already_wyrd_does_nothing(self):
        map_id = esper.create_entity()
        player_eid = create_player(map_id, 10, 10)
        anchor_eid = create_anchor(map_id, 10, 10)

        # Make player already wyrd
        anima_eid = esper.create_entity()
        esper.add_component(player_eid, Wyrd(anima=anima_eid, added_components=[]))

        start_wyrd_prompt(player_eid, anchor_eid)

        # Should not have added a Prompt
        from ninjamagic.component import Prompt

        assert not esper.has_component(player_eid, Prompt)

    def test_adds_prompt_component(self):
        map_id = esper.create_entity()
        player_eid = create_player(map_id, 10, 10)
        anchor_eid = create_anchor(map_id, 10, 10)

        start_wyrd_prompt(player_eid, anchor_eid)

        from ninjamagic.component import Prompt

        assert esper.has_component(player_eid, Prompt)
        prompt = esper.component_for_entity(player_eid, Prompt)
        assert prompt.text == "reach into the fire"

    def test_sends_outbound_prompt(self):
        map_id = esper.create_entity()
        player_eid = create_player(map_id, 10, 10)
        anchor_eid = create_anchor(map_id, 10, 10)

        start_wyrd_prompt(player_eid, anchor_eid)

        prompts = list(bus.iter(bus.OutboundPrompt))
        assert len(prompts) == 1
        assert prompts[0].to == player_eid
        assert prompts[0].text == "reach into the fire"


class TestXpSacrificeCallbacks:
    """Tests for XP sacrifice prompt callbacks."""

    def test_on_xp_sacrifice_ok_enters_wyrd(self):
        map_id = esper.create_entity()
        player_eid = create_player(map_id, 10, 10)
        create_anchor(map_id, 10, 10)  # Needed for find_anchor_at

        # Add some last rest gains
        esper.add_component(player_eid, LastRestGains(gains={"survival": 3}))

        with patch("ninjamagic.wyrd.grow_anchor"):
            on_xp_sacrifice_ok(source=player_eid)

        assert esper.has_component(player_eid, Wyrd)

    def test_on_xp_sacrifice_err_offers_stat_prompt(self):
        map_id = esper.create_entity()
        player_eid = create_player(map_id, 10, 10)
        create_anchor(map_id, 10, 10)

        on_xp_sacrifice_err(source=player_eid)

        from ninjamagic.component import Prompt

        assert esper.has_component(player_eid, Prompt)
        prompt = esper.component_for_entity(player_eid, Prompt)
        # Grace is highest stat
        assert prompt.text == "catch the falling ash"


class TestStatSacrificeCallbacks:
    """Tests for stat sacrifice prompt callbacks."""

    def test_on_stat_sacrifice_ok_enters_wyrd(self):
        map_id = esper.create_entity()
        player_eid = create_player(map_id, 10, 10)
        create_anchor(map_id, 10, 10)

        with patch("ninjamagic.wyrd.grow_anchor"):
            on_stat_sacrifice_ok(source=player_eid, stat="grit")

        assert esper.has_component(player_eid, Wyrd)
        assert esper.has_component(player_eid, StatSickness)

    def test_on_stat_sacrifice_err_cancels(self):
        map_id = esper.create_entity()
        player_eid = create_player(map_id, 10, 10)

        # Should not raise, just echo message
        on_stat_sacrifice_err(source=player_eid)

        assert not esper.has_component(player_eid, Wyrd)


class TestProcess:
    """Tests for wyrd.process()."""

    def test_death_destroys_anima(self):
        map_id = esper.create_entity()
        player_eid = create_player(map_id, 10, 10)
        anchor_eid = create_anchor(map_id, 10, 10)

        with patch("ninjamagic.wyrd.grow_anchor"):
            enter_wyrd_state(player_eid, anchor_eid)

        wyrd = esper.component_for_entity(player_eid, Wyrd)
        anima_eid = wyrd.anima

        # Player dies
        bus.pulse(bus.Die(source=player_eid))
        process()

        assert not esper.entity_exists(anima_eid)
        assert not esper.has_component(player_eid, Wyrd)

    def test_item_dropped_exits_wyrd(self):
        map_id = esper.create_entity()
        player_eid = create_player(map_id, 10, 10)
        anchor_eid = create_anchor(map_id, 10, 10)

        with patch("ninjamagic.wyrd.grow_anchor"):
            enter_wyrd_state(player_eid, anchor_eid)

        wyrd = esper.component_for_entity(player_eid, Wyrd)
        anima_eid = wyrd.anima

        # Player drops anima
        bus.pulse(bus.ItemDropped(source=player_eid, item=anima_eid))
        process()

        assert not esper.has_component(player_eid, Wyrd)

    def test_non_anima_drop_does_not_exit_wyrd(self):
        map_id = esper.create_entity()
        player_eid = create_player(map_id, 10, 10)
        anchor_eid = create_anchor(map_id, 10, 10)

        with patch("ninjamagic.wyrd.grow_anchor"):
            enter_wyrd_state(player_eid, anchor_eid)

        # Create a non-anima item
        other_item = esper.create_entity()
        esper.add_component(other_item, Noun(value="rock", pronoun=Pronouns.IT))

        # Player drops the other item
        bus.pulse(bus.ItemDropped(source=player_eid, item=other_item))
        process()

        # Should still be wyrd
        assert esper.has_component(player_eid, Wyrd)


class TestPutAnimaCreatesAnchor:
    """Tests for Put command: anima + fire = anchor."""

    def test_put_anima_in_fire_creates_anchor(self):
        from ninjamagic.commands import Put
        from ninjamagic.component import ProvidesHeat, ProvidesLight

        map_id = esper.create_entity()
        player_eid = create_player(map_id, 10, 10)
        source_anchor_eid = create_anchor(map_id, 10, 10)

        # Enter wyrd state
        with patch("ninjamagic.wyrd.grow_anchor"):
            enter_wyrd_state(player_eid, source_anchor_eid)

        wyrd_comp = esper.component_for_entity(player_eid, Wyrd)
        anima_eid = wyrd_comp.anima

        # Create a fire (ProvidesHeat) at same tile (reach.adjacent requires same position)
        fire_eid = esper.create_entity()
        esper.add_component(fire_eid, Noun(value="campfire", pronoun=Pronouns.IT))
        esper.add_component(fire_eid, Transform(map_id=map_id, y=10, x=10))
        esper.add_component(fire_eid, ProvidesHeat())
        esper.add_component(fire_eid, ProvidesLight())

        # Create Put command
        put_cmd = Put()
        root = bus.Inbound(source=player_eid, text="put anima in campfire")
        result = put_cmd.trigger(root)

        # Should succeed
        assert result[0] is True

        # Fire should now be an anchor
        assert esper.has_component(fire_eid, Anchor)
        anchor = esper.component_for_entity(fire_eid, Anchor)
        assert anchor.rank == 1

        # Anima should be destroyed
        assert not esper.entity_exists(anima_eid)

        # Player should no longer be wyrd
        assert not esper.has_component(player_eid, Wyrd)

    def test_put_anima_exits_wyrd_for_source_player(self):
        from ninjamagic.commands import Put
        from ninjamagic.component import ProvidesHeat

        map_id = esper.create_entity()
        player_eid = create_player(map_id, 10, 10)
        source_anchor_eid = create_anchor(map_id, 10, 10)

        # Enter wyrd state
        with patch("ninjamagic.wyrd.grow_anchor"):
            enter_wyrd_state(player_eid, source_anchor_eid)

        # Verify components were added
        assert esper.has_component(player_eid, DamageTakenMultiplier)
        assert esper.has_component(player_eid, ProcBonus)

        # Verify wyrd state exists
        assert esper.has_component(player_eid, Wyrd)

        # Create a fire at same tile
        fire_eid = esper.create_entity()
        esper.add_component(fire_eid, Noun(value="fire", pronoun=Pronouns.IT))
        esper.add_component(fire_eid, Transform(map_id=map_id, y=10, x=10))
        esper.add_component(fire_eid, ProvidesHeat())

        # Put anima in fire
        put_cmd = Put()
        root = bus.Inbound(source=player_eid, text="put anima in fire")
        put_cmd.trigger(root)

        # Wyrd components should be removed
        assert not esper.has_component(player_eid, Wyrd)
        assert not esper.has_component(player_eid, DamageTakenMultiplier)
        assert not esper.has_component(player_eid, ProcBonus)
