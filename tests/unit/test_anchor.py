"""Tests for anchor operations: growth, wave mob contest, hostility contest."""

from unittest.mock import patch

import esper
import pytest

from ninjamagic import bus
from ninjamagic.anchor import (
    anchor_contests_hostility,
    anchor_protects,
    any_anchor_protects,
    find_anchor_at,
    grow_anchor,
    process,
    process_end_of_night_contests,
    process_rest_growth,
    wave_mob_attacks_anchor,
)
from ninjamagic.component import (
    Anchor,
    Connection,
    Health,
    Hostility,
    ProvidesHeat,
    ProvidesLight,
    Skills,
    Stance,
    Transform,
)


@pytest.fixture(autouse=True)
def clear_esper():
    """Clear esper database before each test."""
    esper.clear_database()
    bus.clear()
    yield
    esper.clear_database()
    bus.clear()


class TestAnchorProtection:
    """Tests for anchor protection radius."""

    def test_anchor_protects_within_threshold(self):
        """Anchor protects tiles within its threshold."""
        anchor = Anchor(rank=5, threshold=24)
        transform = Transform(map_id=1, y=50, x=50)

        # Adjacent tile - should be protected
        assert anchor_protects(anchor, transform, 50, 51) is True
        # At anchor position - should be protected
        assert anchor_protects(anchor, transform, 50, 50) is True
        # Within manhattan distance < 24 - should be protected
        assert anchor_protects(anchor, transform, 60, 60) is True  # dist = 20

    def test_anchor_does_not_protect_outside_threshold(self):
        """Anchor does not protect tiles outside its threshold."""
        anchor = Anchor(rank=5, threshold=24)
        transform = Transform(map_id=1, y=50, x=50)

        # Outside manhattan distance >= 24 - should NOT be protected
        assert anchor_protects(anchor, transform, 74, 50) is False  # dist = 24
        assert anchor_protects(anchor, transform, 100, 100) is False  # dist = 100

    def test_any_anchor_protects(self):
        """any_anchor_protects checks all anchors on the map."""
        map_id = esper.create_entity()

        # Create an anchor
        anchor_eid = esper.create_entity()
        esper.add_component(anchor_eid, Anchor(rank=5, threshold=24))
        esper.add_component(anchor_eid, Transform(map_id=map_id, y=50, x=50))

        # Tile within protection - should be protected
        assert any_anchor_protects(map_id, 55, 55) is True

        # Tile outside protection - should NOT be protected
        assert any_anchor_protects(map_id, 100, 100) is False

    def test_any_anchor_protects_wrong_map(self):
        """any_anchor_protects returns False for different maps."""
        map_id1 = esper.create_entity()
        map_id2 = esper.create_entity()

        # Create an anchor on map 1
        anchor_eid = esper.create_entity()
        esper.add_component(anchor_eid, Anchor(rank=5, threshold=24))
        esper.add_component(anchor_eid, Transform(map_id=map_id1, y=50, x=50))

        # Checking map 2 - should NOT be protected
        assert any_anchor_protects(map_id2, 50, 50) is False


class TestFindAnchorAt:
    """Tests for finding anchors at specific positions."""

    def test_find_anchor_at_exact_position(self):
        """find_anchor_at returns anchor at exact position."""
        map_id = esper.create_entity()

        anchor_eid = esper.create_entity()
        esper.add_component(anchor_eid, Anchor(rank=5))
        esper.add_component(anchor_eid, Transform(map_id=map_id, y=10, x=20))

        assert find_anchor_at(map_id, 10, 20) == anchor_eid

    def test_find_anchor_at_wrong_position(self):
        """find_anchor_at returns None for wrong position."""
        map_id = esper.create_entity()

        anchor_eid = esper.create_entity()
        esper.add_component(anchor_eid, Anchor(rank=5))
        esper.add_component(anchor_eid, Transform(map_id=map_id, y=10, x=20))

        assert find_anchor_at(map_id, 10, 21) is None

    def test_find_anchor_at_no_anchor(self):
        """find_anchor_at returns None when no anchor exists."""
        map_id = esper.create_entity()
        assert find_anchor_at(map_id, 10, 20) is None


class TestAnchorGrowth:
    """Tests for anchor growth from resting."""

    def test_grow_anchor_success(self):
        """Anchor grows when player wins the contest."""
        map_id = esper.create_entity()
        anchor_eid = esper.create_entity()
        esper.add_component(anchor_eid, Anchor(rank=1))
        esper.add_component(anchor_eid, Transform(map_id=map_id, y=10, x=10))

        # High player rank should win against low anchor rank
        with patch("ninjamagic.anchor.Trial.check", return_value=True):
            result = grow_anchor(anchor_eid, player_rank=50)

        assert result is True
        assert esper.component_for_entity(anchor_eid, Anchor).rank == 2

    def test_grow_anchor_failure(self):
        """Anchor does not grow when player loses the contest."""
        map_id = esper.create_entity()
        anchor_eid = esper.create_entity()
        esper.add_component(anchor_eid, Anchor(rank=10))
        esper.add_component(anchor_eid, Transform(map_id=map_id, y=10, x=10))

        with patch("ninjamagic.anchor.Trial.check", return_value=False):
            result = grow_anchor(anchor_eid, player_rank=5)

        assert result is False
        assert esper.component_for_entity(anchor_eid, Anchor).rank == 10


class TestWaveMobContest:
    """Tests for wave mob attacking anchor."""

    def test_wave_mob_damages_anchor(self):
        """Anchor loses rank when mob wins contest."""
        anchor_eid = esper.create_entity()
        esper.add_component(anchor_eid, Anchor(rank=5))
        esper.add_component(anchor_eid, Transform(map_id=1, y=10, x=10))

        with patch("ninjamagic.anchor.Trial.check", return_value=True):
            result = wave_mob_attacks_anchor(anchor_eid, mob_strength=10)

        assert result is True
        assert esper.component_for_entity(anchor_eid, Anchor).rank == 4

    def test_anchor_defends_against_mob(self):
        """Anchor rank unchanged when it wins contest."""
        anchor_eid = esper.create_entity()
        esper.add_component(anchor_eid, Anchor(rank=10))
        esper.add_component(anchor_eid, Transform(map_id=1, y=10, x=10))

        with patch("ninjamagic.anchor.Trial.check", return_value=False):
            result = wave_mob_attacks_anchor(anchor_eid, mob_strength=1)

        assert result is False
        assert esper.component_for_entity(anchor_eid, Anchor).rank == 10

    def test_anchor_destroyed_at_zero_rank(self):
        """AnchorDestroyed signal pulsed when rank reaches 0."""
        anchor_eid = esper.create_entity()
        esper.add_component(anchor_eid, Anchor(rank=1))
        esper.add_component(anchor_eid, Transform(map_id=1, y=10, x=10))

        with patch("ninjamagic.anchor.Trial.check", return_value=True):
            wave_mob_attacks_anchor(anchor_eid, mob_strength=10)

        # Should have pulsed AnchorDestroyed
        signals = list(bus.iter(bus.AnchorDestroyed))
        assert len(signals) == 1
        assert signals[0].anchor == anchor_eid


class TestHostilityContest:
    """Tests for end-of-night anchor vs hostility contest."""

    def test_anchor_survives_no_hostility(self):
        """Anchor survives when map has no hostility."""
        map_id = esper.create_entity()
        anchor_eid = esper.create_entity()
        esper.add_component(anchor_eid, Anchor(rank=5))
        esper.add_component(anchor_eid, Transform(map_id=map_id, y=10, x=10))

        result = anchor_contests_hostility(anchor_eid)

        assert result is True
        assert len(list(bus.iter(bus.AnchorDestroyed))) == 0

    def test_anchor_survives_with_high_rank(self):
        """Anchor survives when it wins against hostility."""
        map_id = esper.create_entity()
        esper.add_component(map_id, Hostility(base=10))

        anchor_eid = esper.create_entity()
        esper.add_component(anchor_eid, Anchor(rank=50))
        esper.add_component(anchor_eid, Transform(map_id=map_id, y=10, x=10))

        with patch("ninjamagic.anchor.Trial.check", return_value=True):
            result = anchor_contests_hostility(anchor_eid)

        assert result is True
        assert len(list(bus.iter(bus.AnchorDestroyed))) == 0

    def test_anchor_destroyed_by_hostility(self):
        """Anchor destroyed when it loses against hostility."""
        map_id = esper.create_entity()
        esper.add_component(map_id, Hostility(base=100))

        anchor_eid = esper.create_entity()
        esper.add_component(anchor_eid, Anchor(rank=1))
        esper.add_component(anchor_eid, Transform(map_id=map_id, y=10, x=10))

        with patch("ninjamagic.anchor.Trial.check", return_value=False):
            result = anchor_contests_hostility(anchor_eid)

        assert result is False
        signals = list(bus.iter(bus.AnchorDestroyed))
        assert len(signals) == 1
        assert signals[0].anchor == anchor_eid

    def test_hostility_uses_tile_specific_value(self):
        """Hostility uses tile-specific value when available."""
        map_id = esper.create_entity()
        esper.add_component(
            map_id,
            Hostility(
                base=10,
                tiles={(10, 10): 100},  # High hostility at anchor position
            ),
        )

        anchor_eid = esper.create_entity()
        esper.add_component(anchor_eid, Anchor(rank=5))
        esper.add_component(anchor_eid, Transform(map_id=map_id, y=10, x=10))

        with patch("ninjamagic.anchor.Trial.check", return_value=False):
            result = anchor_contests_hostility(anchor_eid)

        # Should lose due to high tile-specific hostility
        assert result is False


class MockWebSocket:
    """Stub for Connection component in tests."""

    pass


class TestProcessRestGrowth:
    """Tests for process_rest_growth during RestCheck."""

    def _create_camping_player(self, map_id: int, y: int, x: int, *, anchor_eid: int = 0) -> int:
        """Helper to create a player camping at a position."""
        player_eid = esper.create_entity()
        esper.add_component(player_eid, MockWebSocket(), Connection)
        esper.add_component(player_eid, Transform(map_id=map_id, y=y, x=x))
        esper.add_component(player_eid, Health(cur=100.0))
        esper.add_component(player_eid, Skills())
        # Camping stance - sitting at the anchor
        esper.add_component(player_eid, Stance(cur="sitting", prop=anchor_eid or 0))
        return player_eid

    def test_process_rest_growth_at_anchor(self):
        """Players resting at anchor can grow it."""
        map_id = esper.create_entity()

        # Create anchor with heat and light (to be valid camping prop)
        anchor_eid = esper.create_entity()
        esper.add_component(anchor_eid, Anchor(rank=1))
        esper.add_component(anchor_eid, Transform(map_id=map_id, y=10, x=10))
        esper.add_component(anchor_eid, ProvidesHeat())
        esper.add_component(anchor_eid, ProvidesLight())

        # Create player camping at anchor position
        player_eid = self._create_camping_player(map_id, 10, 10, anchor_eid=anchor_eid)
        skills = esper.component_for_entity(player_eid, Skills)
        skills.survival.rank = 50  # High survival rank

        with patch("ninjamagic.anchor.Trial.check", return_value=True):
            process_rest_growth()

        # Anchor should have grown
        assert esper.component_for_entity(anchor_eid, Anchor).rank == 2

    def test_process_rest_growth_not_at_anchor(self):
        """Players not at anchor position don't grow it."""
        map_id = esper.create_entity()

        anchor_eid = esper.create_entity()
        esper.add_component(anchor_eid, Anchor(rank=1))
        esper.add_component(anchor_eid, Transform(map_id=map_id, y=10, x=10))
        esper.add_component(anchor_eid, ProvidesHeat())
        esper.add_component(anchor_eid, ProvidesLight())

        # Create player camping at DIFFERENT position
        self._create_camping_player(map_id, 20, 20, anchor_eid=anchor_eid)

        with patch("ninjamagic.anchor.Trial.check", return_value=True):
            process_rest_growth()

        # Anchor should NOT have grown
        assert esper.component_for_entity(anchor_eid, Anchor).rank == 1

    def test_process_rest_growth_not_camping(self):
        """Players not camping don't grow anchor."""
        map_id = esper.create_entity()

        anchor_eid = esper.create_entity()
        esper.add_component(anchor_eid, Anchor(rank=1))
        esper.add_component(anchor_eid, Transform(map_id=map_id, y=10, x=10))

        # Create player at anchor position but standing (not camping)
        player_eid = esper.create_entity()
        esper.add_component(player_eid, MockWebSocket(), Connection)
        esper.add_component(player_eid, Transform(map_id=map_id, y=10, x=10))
        esper.add_component(player_eid, Health(cur=100.0))
        esper.add_component(player_eid, Skills())
        esper.add_component(player_eid, Stance(cur="standing", prop=0))

        with patch("ninjamagic.anchor.Trial.check", return_value=True):
            process_rest_growth()

        # Anchor should NOT have grown
        assert esper.component_for_entity(anchor_eid, Anchor).rank == 1


class TestProcessEndOfNightContests:
    """Tests for process_end_of_night_contests."""

    def test_processes_all_anchors(self):
        """All anchors are checked against hostility."""
        map_id = esper.create_entity()
        esper.add_component(map_id, Hostility(base=1))

        # Create multiple anchors
        anchor1 = esper.create_entity()
        esper.add_component(anchor1, Anchor(rank=10))
        esper.add_component(anchor1, Transform(map_id=map_id, y=10, x=10))

        anchor2 = esper.create_entity()
        esper.add_component(anchor2, Anchor(rank=10))
        esper.add_component(anchor2, Transform(map_id=map_id, y=50, x=50))

        with patch("ninjamagic.anchor.Trial.check", return_value=True):
            process_end_of_night_contests()

        # Both anchors should still exist
        assert esper.entity_exists(anchor1)
        assert esper.entity_exists(anchor2)


class TestProcess:
    """Tests for the main process function."""

    def test_process_handles_anchor_destroyed(self):
        """process() deletes anchors when AnchorDestroyed is pulsed."""
        anchor_eid = esper.create_entity()
        esper.add_component(anchor_eid, Anchor(rank=1))
        esper.add_component(anchor_eid, Transform(map_id=1, y=10, x=10))

        # Pulse destruction signal
        bus.pulse(bus.AnchorDestroyed(anchor=anchor_eid))

        process()

        # Anchor should be deleted
        assert not esper.entity_exists(anchor_eid)

    def test_process_handles_wave_mob_attack(self):
        """process() handles WaveMobAttacksAnchor signals."""
        anchor_eid = esper.create_entity()
        esper.add_component(anchor_eid, Anchor(rank=5))
        esper.add_component(anchor_eid, Transform(map_id=1, y=10, x=10))

        # Pulse attack signal
        bus.pulse(bus.WaveMobAttacksAnchor(anchor=anchor_eid, mob_strength=10))

        with patch("ninjamagic.anchor.Trial.check", return_value=True):
            process()

        # Anchor should have lost rank
        assert esper.component_for_entity(anchor_eid, Anchor).rank == 4

    def test_process_on_rest_check(self):
        """process() runs rest growth and hostility contests on RestCheck."""
        map_id = esper.create_entity()
        esper.add_component(map_id, Hostility(base=1))

        anchor_eid = esper.create_entity()
        esper.add_component(anchor_eid, Anchor(rank=10))
        esper.add_component(anchor_eid, Transform(map_id=map_id, y=10, x=10))

        # Pulse RestCheck
        bus.pulse(bus.RestCheck())

        with patch("ninjamagic.anchor.Trial.check", return_value=True):
            process()

        # Anchor should still exist (passed hostility check)
        assert esper.entity_exists(anchor_eid)
