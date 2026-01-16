# tests/test_behavior.py
"""Tests for behavior priority queue system."""

import esper
import pytest

from ninjamagic import bus
from ninjamagic.behavior import (
    Attack,
    FlankTarget,
    FleeFromEntity,
    PathTowardCoordinate,
    PathTowardEntity,
    SelectNearestAnchor,
    SelectNearestPlayer,
    UseAbility,
    Wait,
    can_execute,
    execute,
    process_behavior_queue,
)
from ninjamagic.component import (
    Anchor,
    BehaviorQueue,
    Connection,
    Health,
    Target,
    Transform,
)


@pytest.fixture(autouse=True)
def reset_esper():
    """Reset esper world before each test."""
    esper.clear_database()
    bus.clear()
    yield
    esper.clear_database()
    bus.clear()


@pytest.fixture
def map_entity():
    """Create a map entity with walkable terrain."""
    from ninjamagic.world.state import build_nowhere

    return build_nowhere()


@pytest.fixture
def mob(map_entity):
    """Create a mob entity at (5, 5)."""
    eid = esper.create_entity(
        Transform(map_id=map_entity, y=5, x=5),
        Health(),
    )
    return eid


@pytest.fixture
def player(map_entity):
    """Create a player entity at (10, 10)."""

    # Create a mock websocket-like object for Connection
    class MockWebSocket:
        pass

    eid = esper.create_entity(
        Transform(map_id=map_entity, y=10, x=10),
        Health(),
    )
    esper.add_component(eid, MockWebSocket(), Connection)
    return eid


@pytest.fixture
def anchor(map_entity):
    """Create an anchor entity at (15, 15)."""
    eid = esper.create_entity(
        Transform(map_id=map_entity, y=15, x=15),
        Anchor(rank=1),
    )
    return eid


class TestSelectNearestPlayer:
    def test_can_execute_with_player(self, mob, player):
        """Can execute when player exists."""
        assert can_execute(SelectNearestPlayer(), mob)

    def test_can_execute_without_player(self, mob):
        """Cannot execute when no players exist."""
        assert not can_execute(SelectNearestPlayer(), mob)

    def test_execute_sets_target(self, mob, player):
        """Execute sets Target to nearest player."""
        assert execute(SelectNearestPlayer(), mob)
        target = esper.component_for_entity(mob, Target)
        assert target.entity == player

    def test_finds_nearest_of_multiple(self, mob, player, map_entity):
        """Finds nearest when multiple players exist."""

        class MockWebSocket:
            pass

        closer_player = esper.create_entity(
            Transform(map_id=map_entity, y=6, x=6),
            Health(),
        )
        esper.add_component(closer_player, MockWebSocket(), Connection)

        execute(SelectNearestPlayer(), mob)
        target = esper.component_for_entity(mob, Target)
        assert target.entity == closer_player


class TestSelectNearestAnchor:
    def test_can_execute_with_anchor(self, mob, anchor):
        """Can execute when anchor exists."""
        assert can_execute(SelectNearestAnchor(), mob)

    def test_can_execute_without_anchor(self, mob):
        """Cannot execute when no anchors exist."""
        assert not can_execute(SelectNearestAnchor(), mob)

    def test_execute_sets_target(self, mob, anchor):
        """Execute sets Target to nearest anchor."""
        assert execute(SelectNearestAnchor(), mob)
        target = esper.component_for_entity(mob, Target)
        assert target.entity == anchor


class TestPathTowardEntity:
    def test_can_execute_with_target(self, mob, player):
        """Can execute when target exists and not at target."""
        esper.add_component(mob, Target(entity=player))
        assert can_execute(PathTowardEntity(), mob)

    def test_cannot_execute_without_target(self, mob):
        """Cannot execute when no target."""
        assert not can_execute(PathTowardEntity(), mob)

    def test_cannot_execute_at_target(self, mob, map_entity):
        """Cannot execute when already at target location."""
        other = esper.create_entity(Transform(map_id=map_entity, y=5, x=5))
        esper.add_component(mob, Target(entity=other))
        assert not can_execute(PathTowardEntity(), mob)

    def test_execute_pulses_move(self, mob, player):
        """Execute pulses MovePosition toward target."""
        esper.add_component(mob, Target(entity=player))
        execute(PathTowardEntity(), mob)

        moves = list(bus.iter(bus.MovePosition))
        assert len(moves) == 1
        assert moves[0].source == mob
        # Should move toward player (10, 10) from mob (5, 5)
        # Direction should be southeast
        assert moves[0].to_y >= 5
        assert moves[0].to_x >= 5


class TestPathTowardCoordinate:
    def test_can_execute_when_not_at_coord(self, mob):
        """Can execute when not at coordinate."""
        assert can_execute(PathTowardCoordinate(y=10, x=10), mob)

    def test_cannot_execute_at_coord(self, mob):
        """Cannot execute when at coordinate."""
        assert not can_execute(PathTowardCoordinate(y=5, x=5), mob)

    def test_execute_pulses_move(self, mob):
        """Execute pulses MovePosition toward coordinate."""
        execute(PathTowardCoordinate(y=10, x=10), mob)

        moves = list(bus.iter(bus.MovePosition))
        assert len(moves) == 1
        assert moves[0].source == mob


class TestAttack:
    def test_can_execute_when_adjacent(self, mob, map_entity):
        """Can execute when adjacent to target."""
        adjacent_target = esper.create_entity(
            Transform(map_id=map_entity, y=5, x=6),
            Health(),
        )
        esper.add_component(mob, Target(entity=adjacent_target))
        assert can_execute(Attack(), mob)

    def test_cannot_execute_when_not_adjacent(self, mob, player):
        """Cannot execute when not adjacent to target."""
        esper.add_component(mob, Target(entity=player))
        assert not can_execute(Attack(), mob)

    def test_cannot_execute_without_target(self, mob):
        """Cannot execute without target."""
        assert not can_execute(Attack(), mob)

    def test_execute_pulses_melee(self, mob, map_entity):
        """Execute pulses Melee signal."""
        adjacent_target = esper.create_entity(
            Transform(map_id=map_entity, y=5, x=6),
            Health(),
        )
        esper.add_component(mob, Target(entity=adjacent_target))

        execute(Attack(), mob)

        melees = list(bus.iter(bus.Melee))
        assert len(melees) == 1
        assert melees[0].source == mob
        assert melees[0].target == adjacent_target


class TestFlankTarget:
    def test_can_execute_when_not_adjacent(self, mob, player):
        """Can execute when not adjacent to target."""
        esper.add_component(mob, Target(entity=player))
        assert can_execute(FlankTarget(), mob)

    def test_cannot_execute_when_adjacent(self, mob, map_entity):
        """Cannot execute when already adjacent."""
        adjacent_target = esper.create_entity(
            Transform(map_id=map_entity, y=5, x=6),
            Health(),
        )
        esper.add_component(mob, Target(entity=adjacent_target))
        assert not can_execute(FlankTarget(), mob)

    def test_execute_moves_toward_flanking(self, mob, player):
        """Execute moves toward flanking position."""
        esper.add_component(mob, Target(entity=player))
        execute(FlankTarget(), mob)

        moves = list(bus.iter(bus.MovePosition))
        assert len(moves) == 1
        assert moves[0].source == mob


class TestFleeFromEntity:
    def test_can_execute_with_target(self, mob, player):
        """Can execute when target exists."""
        esper.add_component(mob, Target(entity=player))
        assert can_execute(FleeFromEntity(), mob)

    def test_cannot_execute_without_target(self, mob):
        """Cannot execute without target."""
        assert not can_execute(FleeFromEntity(), mob)

    def test_execute_moves_away(self, mob, player):
        """Execute moves away from target."""
        esper.add_component(mob, Target(entity=player))
        execute(FleeFromEntity(), mob)

        moves = list(bus.iter(bus.MovePosition))
        assert len(moves) == 1
        # Should move away from player (10, 10)
        # Mob at (5, 5), should move toward lower coordinates
        assert moves[0].to_y <= 5 or moves[0].to_x <= 5


class TestWait:
    def test_can_always_execute(self, mob):
        """Wait can always execute."""
        assert can_execute(Wait(), mob)

    def test_execute_does_nothing(self, mob):
        """Wait does nothing."""
        assert execute(Wait(), mob)
        # No signals pulsed
        assert list(bus.iter(bus.MovePosition)) == []
        assert list(bus.iter(bus.Melee)) == []


class TestUseAbility:
    def test_can_execute(self, mob):
        """UseAbility can execute (placeholder)."""
        assert can_execute(UseAbility(ability="fireball"), mob)

    def test_execute_succeeds(self, mob):
        """UseAbility execution succeeds (placeholder)."""
        assert execute(UseAbility(ability="fireball"), mob)


class TestProcessBehaviorQueue:
    def test_processes_first_successful(self, mob, player):
        """Processes behaviors in order, stops at first success."""
        behaviors = [
            SelectNearestPlayer(),
            PathTowardEntity(),
            Wait(),
        ]

        result = process_behavior_queue(mob, behaviors)

        assert result is True
        # Should have set target (first behavior succeeded)
        assert esper.has_component(mob, Target)

    def test_skips_failed_behaviors(self, mob, player):
        """Skips behaviors that cannot execute."""
        behaviors = [
            Attack(),  # Cannot execute - not adjacent
            SelectNearestPlayer(),  # Can execute
            Wait(),
        ]

        result = process_behavior_queue(mob, behaviors)

        assert result is True
        # Attack skipped, SelectNearestPlayer succeeded
        assert esper.has_component(mob, Target)
        # No melee signal
        assert list(bus.iter(bus.Melee)) == []

    def test_returns_false_if_all_fail(self, mob):
        """Returns False if no behaviors succeed."""
        behaviors = [
            Attack(),  # No target
            PathTowardEntity(),  # No target
        ]

        result = process_behavior_queue(mob, behaviors)

        assert result is False

    def test_empty_queue(self, mob):
        """Empty behavior queue returns False."""
        result = process_behavior_queue(mob, [])
        assert result is False


class TestBehaviorQueueComponent:
    def test_component_stores_behaviors(self, mob):
        """BehaviorQueue component stores list of behaviors."""
        behaviors = [SelectNearestPlayer(), Attack(), Wait()]
        esper.add_component(mob, BehaviorQueue(behaviors=behaviors))

        queue = esper.component_for_entity(mob, BehaviorQueue)
        assert len(queue.behaviors) == 3
        assert isinstance(queue.behaviors[0], SelectNearestPlayer)
        assert isinstance(queue.behaviors[1], Attack)
        assert isinstance(queue.behaviors[2], Wait)
