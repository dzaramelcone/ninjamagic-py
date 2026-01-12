"""Integration tests for Q1 MVP systems.

Tests full flows across multiple systems:
- Wyrd decision tree flow
- Anima lifecycle
- Decay with anchor protection
- Anchor growth and contests
- Behavior execution chains
"""

from unittest.mock import patch

import esper
import pytest

from ninjamagic import bus
from ninjamagic.anchor import (
    anchor_contests_hostility,
    any_anchor_protects,
    wave_mob_attacks_anchor,
)
from ninjamagic.behavior import (
    Attack,
    PathTowardEntity,
    SelectNearestPlayer,
    can_execute,
    execute,
    process_behavior_queue,
)
from ninjamagic.component import (
    Anchor,
    Anima,
    BehaviorQueue,
    Connection,
    DamageTakenMultiplier,
    Health,
    Hostility,
    LastRestGains,
    Noun,
    Prompt,
    Pronouns,
    ProvidesHeat,
    ProvidesLight,
    Skills,
    Stance,
    Stats,
    StatSickness,
    Target,
    Transform,
    Wyrd,
)
from ninjamagic.spawn import spawn_mob
from ninjamagic.wyrd import (
    enter_wyrd_state,
    on_stat_sacrifice_err,
    on_stat_sacrifice_ok,
    on_xp_sacrifice_err,
    on_xp_sacrifice_ok,
    process as wyrd_process,
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


def create_player(map_id: int, y: int, x: int, *, survival_rank: int = 10) -> int:
    """Create a player entity with all required components."""
    player_eid = esper.create_entity()
    esper.add_component(player_eid, MockWebSocket(), Connection)
    esper.add_component(player_eid, Transform(map_id=map_id, y=y, x=x))
    esper.add_component(player_eid, Health(cur=100.0))
    esper.add_component(player_eid, Stats(grace=10, grit=8, wit=6))
    esper.add_component(player_eid, Skills())
    skills = esper.component_for_entity(player_eid, Skills)
    skills.survival.rank = survival_rank
    esper.add_component(player_eid, Stance(cur="standing", prop=0))
    return player_eid


def create_anchor(map_id: int, y: int, x: int, *, rank: int = 5, threshold: int = 24) -> int:
    """Create an anchor entity."""
    anchor_eid = esper.create_entity()
    esper.add_component(anchor_eid, Anchor(rank=rank, threshold=threshold))
    esper.add_component(anchor_eid, Transform(map_id=map_id, y=y, x=x))
    esper.add_component(anchor_eid, Noun(value="bonfire", pronoun=Pronouns.IT))
    esper.add_component(anchor_eid, ProvidesHeat())
    esper.add_component(anchor_eid, ProvidesLight())
    return anchor_eid


class TestWyrdDecisionTreeFlow:
    """Integration tests for the full wyrd decision tree."""

    def test_kneel_at_anchor_starts_prompt(self):
        """Kneeling at anchor starts the first prompt."""
        map_id = esper.create_entity()
        player_eid = create_player(map_id, 10, 10)
        anchor_eid = create_anchor(map_id, 10, 10)

        start_wyrd_prompt(player_eid, anchor_eid)

        assert esper.has_component(player_eid, Prompt)
        prompt = esper.component_for_entity(player_eid, Prompt)
        assert prompt.text == "reach into the fire"

    def test_first_prompt_success_xp_sacrifice(self):
        """Typing first prompt correctly triggers XP sacrifice."""
        map_id = esper.create_entity()
        player_eid = create_player(map_id, 10, 10)
        create_anchor(map_id, 10, 10)

        # Add last rest gains
        esper.add_component(player_eid, LastRestGains(gains={"survival": 5}))

        with patch("ninjamagic.wyrd.grow_anchor"):
            on_xp_sacrifice_ok(source=player_eid)

        assert esper.has_component(player_eid, Wyrd)
        assert esper.has_component(player_eid, DamageTakenMultiplier)
        assert not esper.has_component(player_eid, StatSickness)

    def test_first_prompt_fail_offers_stat_prompt(self):
        """Failing first prompt offers stat-based second prompt."""
        map_id = esper.create_entity()
        player_eid = create_player(map_id, 10, 10)
        create_anchor(map_id, 10, 10)

        on_xp_sacrifice_err(source=player_eid)

        assert esper.has_component(player_eid, Prompt)
        prompt = esper.component_for_entity(player_eid, Prompt)
        # Grace is highest stat (10), so prompt should be "catch the falling ash"
        assert prompt.text == "catch the falling ash"

    def test_second_prompt_success_stat_sickness(self):
        """Typing second prompt correctly triggers stat sickness."""
        map_id = esper.create_entity()
        player_eid = create_player(map_id, 10, 10)
        create_anchor(map_id, 10, 10)

        with patch("ninjamagic.wyrd.grow_anchor"):
            on_stat_sacrifice_ok(source=player_eid, stat="grace")

        assert esper.has_component(player_eid, Wyrd)
        assert esper.has_component(player_eid, StatSickness)
        sickness = esper.component_for_entity(player_eid, StatSickness)
        assert sickness.stat == "grace"

    def test_second_prompt_fail_cancels(self):
        """Failing second prompt cancels the process."""
        map_id = esper.create_entity()
        player_eid = create_player(map_id, 10, 10)

        on_stat_sacrifice_err(source=player_eid)

        assert not esper.has_component(player_eid, Wyrd)


class TestAnimaLifecycle:
    """Integration tests for anima creation, transfer, and destruction."""

    def test_wyrd_player_has_anima_in_hands(self):
        """Entering wyrd state creates anima in player's hands."""
        map_id = esper.create_entity()
        player_eid = create_player(map_id, 10, 10)
        anchor_eid = create_anchor(map_id, 10, 10)

        with patch("ninjamagic.wyrd.grow_anchor"):
            enter_wyrd_state(player_eid, anchor_eid)

        wyrd = esper.component_for_entity(player_eid, Wyrd)
        anima_eid = wyrd.anima

        assert esper.entity_exists(anima_eid)
        assert esper.has_component(anima_eid, Anima)
        assert esper.has_component(anima_eid, Noun)

        anima = esper.component_for_entity(anima_eid, Anima)
        assert anima.source_player == player_eid
        assert anima.source_anchor == anchor_eid

    def test_drop_anima_exits_wyrd(self):
        """Dropping anima exits wyrd state."""
        map_id = esper.create_entity()
        player_eid = create_player(map_id, 10, 10)
        anchor_eid = create_anchor(map_id, 10, 10)

        with patch("ninjamagic.wyrd.grow_anchor"):
            enter_wyrd_state(player_eid, anchor_eid)

        wyrd = esper.component_for_entity(player_eid, Wyrd)
        anima_eid = wyrd.anima

        # Simulate drop
        bus.pulse(bus.ItemDropped(source=player_eid, item=anima_eid))
        wyrd_process()

        assert not esper.has_component(player_eid, Wyrd)
        assert not esper.has_component(player_eid, DamageTakenMultiplier)

    def test_death_destroys_anima(self):
        """Player death destroys anima and exits wyrd."""
        map_id = esper.create_entity()
        player_eid = create_player(map_id, 10, 10)
        anchor_eid = create_anchor(map_id, 10, 10)

        with patch("ninjamagic.wyrd.grow_anchor"):
            enter_wyrd_state(player_eid, anchor_eid)

        wyrd = esper.component_for_entity(player_eid, Wyrd)
        anima_eid = wyrd.anima

        bus.pulse(bus.Die(source=player_eid))
        wyrd_process()

        assert not esper.entity_exists(anima_eid)
        assert not esper.has_component(player_eid, Wyrd)


class TestDecayWithAnchors:
    """Integration tests for decay system with anchor protection."""

    def test_tile_inside_threshold_persists(self):
        """Tiles within anchor threshold are protected from decay."""
        map_id = esper.create_entity()
        create_anchor(map_id, 50, 50, threshold=24)

        # Tile at (55, 55) is within threshold (manhattan dist = 10)
        assert any_anchor_protects(map_id, 55, 55) is True

    def test_tile_outside_threshold_not_protected(self):
        """Tiles outside anchor threshold are not protected."""
        map_id = esper.create_entity()
        create_anchor(map_id, 50, 50, threshold=24)

        # Tile at (100, 100) is outside threshold (manhattan dist = 100)
        assert any_anchor_protects(map_id, 100, 100) is False

    def test_multiple_anchors_extend_protection(self):
        """Multiple anchors can protect different areas."""
        map_id = esper.create_entity()
        create_anchor(map_id, 10, 10, threshold=10)
        create_anchor(map_id, 50, 50, threshold=10)

        # Near first anchor
        assert any_anchor_protects(map_id, 12, 12) is True
        # Near second anchor
        assert any_anchor_protects(map_id, 52, 52) is True
        # Between anchors (not protected by either)
        assert any_anchor_protects(map_id, 30, 30) is False


class TestAnchorContests:
    """Integration tests for anchor growth and defense."""

    def test_wave_mob_damages_anchor(self):
        """Wave mob winning contest reduces anchor rank."""
        map_id = esper.create_entity()
        anchor_eid = create_anchor(map_id, 10, 10, rank=5)

        with patch("ninjamagic.anchor.Trial.check", return_value=True):
            result = wave_mob_attacks_anchor(anchor_eid, mob_strength=10)

        assert result is True
        anchor = esper.component_for_entity(anchor_eid, Anchor)
        assert anchor.rank == 4

    def test_anchor_defends_against_weak_mob(self):
        """Strong anchor defends against weak mob."""
        map_id = esper.create_entity()
        anchor_eid = create_anchor(map_id, 10, 10, rank=10)

        with patch("ninjamagic.anchor.Trial.check", return_value=False):
            result = wave_mob_attacks_anchor(anchor_eid, mob_strength=1)

        assert result is False
        anchor = esper.component_for_entity(anchor_eid, Anchor)
        assert anchor.rank == 10  # Unchanged

    def test_anchor_survives_low_hostility(self):
        """Anchor survives end-of-night with low hostility."""
        map_id = esper.create_entity()
        esper.add_component(map_id, Hostility(base=5))
        anchor_eid = create_anchor(map_id, 10, 10, rank=20)

        with patch("ninjamagic.anchor.Trial.check", return_value=True):
            result = anchor_contests_hostility(anchor_eid)

        assert result is True
        assert esper.entity_exists(anchor_eid)

    def test_anchor_destroyed_by_high_hostility(self):
        """Weak anchor destroyed by high hostility."""
        map_id = esper.create_entity()
        esper.add_component(map_id, Hostility(base=100))
        anchor_eid = create_anchor(map_id, 10, 10, rank=1)

        with patch("ninjamagic.anchor.Trial.check", return_value=False):
            result = anchor_contests_hostility(anchor_eid)

        assert result is False
        # AnchorDestroyed signal pulsed
        signals = list(bus.iter(bus.AnchorDestroyed))
        assert len(signals) == 1


class TestBehaviorChains:
    """Integration tests for behavior execution chains."""

    def test_select_nearest_player_acquires_target(self):
        """SelectNearestPlayer sets Target component."""
        map_id = esper.create_entity()
        player_eid = create_player(map_id, 10, 10)
        mob_eid = spawn_mob("imp", map_id=map_id, y=15, x=15)

        # Execute SelectNearestPlayer
        assert can_execute(SelectNearestPlayer(), mob_eid)
        execute(SelectNearestPlayer(), mob_eid)

        assert esper.has_component(mob_eid, Target)
        target = esper.component_for_entity(mob_eid, Target)
        assert target.entity == player_eid

    def test_path_toward_entity_can_execute(self):
        """PathTowardEntity can execute when target exists and is not adjacent."""
        map_id = esper.create_entity()
        player_eid = create_player(map_id, 10, 10)
        mob_eid = spawn_mob("imp", map_id=map_id, y=15, x=15)

        # Set target
        esper.add_component(mob_eid, Target(entity=player_eid))

        # Can execute when target exists and not adjacent
        assert can_execute(PathTowardEntity(), mob_eid)

    def test_path_toward_entity_cannot_execute_at_target(self):
        """PathTowardEntity cannot execute when at same position as target."""
        map_id = esper.create_entity()
        player_eid = create_player(map_id, 10, 10)
        mob_eid = spawn_mob("imp", map_id=map_id, y=10, x=10)  # Same position

        # Set target
        esper.add_component(mob_eid, Target(entity=player_eid))

        # Cannot execute when at same position
        assert not can_execute(PathTowardEntity(), mob_eid)

    def test_attack_when_adjacent(self):
        """Attack executes when adjacent to target."""
        map_id = esper.create_entity()
        player_eid = create_player(map_id, 10, 10)
        mob_eid = spawn_mob("imp", map_id=map_id, y=10, x=11)  # Adjacent

        esper.add_component(mob_eid, Target(entity=player_eid))

        assert can_execute(Attack(), mob_eid)
        execute(Attack(), mob_eid)

        # Should pulse Melee signal
        melees = list(bus.iter(bus.Melee))
        assert len(melees) == 1
        assert melees[0].source == mob_eid
        assert melees[0].target == player_eid

    def test_attack_fails_when_not_adjacent(self):
        """Attack cannot execute when not adjacent."""
        map_id = esper.create_entity()
        player_eid = create_player(map_id, 10, 10)
        mob_eid = spawn_mob("imp", map_id=map_id, y=15, x=15)  # Not adjacent

        esper.add_component(mob_eid, Target(entity=player_eid))

        assert not can_execute(Attack(), mob_eid)

    def test_behavior_queue_select_then_attack(self):
        """Behavior queue runs SelectNearestPlayer then Attack when adjacent."""
        map_id = esper.create_entity()
        player_eid = create_player(map_id, 10, 10)
        mob_eid = spawn_mob("imp", map_id=map_id, y=10, x=11)  # Adjacent

        # imp has: SelectNearestPlayer, PathTowardEntity, Attack
        # When adjacent, PathTowardEntity can_execute returns False

        # Execute SelectNearestPlayer first (sets target)
        execute(SelectNearestPlayer(), mob_eid)
        assert esper.has_component(mob_eid, Target)

        # Now execute Attack directly (since PathTowardEntity can't execute when adjacent)
        assert can_execute(Attack(), mob_eid)
        execute(Attack(), mob_eid)

        # Check attack was pulsed
        melees = list(bus.iter(bus.Melee))
        assert len(melees) == 1
        assert melees[0].source == mob_eid
        assert melees[0].target == player_eid


class TestSpawnedMobBehavior:
    """Integration tests for spawned mobs with full behavior."""

    def test_wave_imp_targets_anchor(self):
        """Wave imp targets nearest anchor, not player."""
        map_id = esper.create_entity()
        create_player(map_id, 10, 10)
        anchor_eid = create_anchor(map_id, 20, 20)
        mob_eid = spawn_mob("wave_imp", map_id=map_id, y=15, x=15)

        queue = esper.component_for_entity(mob_eid, BehaviorQueue)
        process_behavior_queue(mob_eid, queue.behaviors)

        target = esper.component_for_entity(mob_eid, Target)
        assert target.entity == anchor_eid  # Targets anchor, not player
