"""Tests for mob spawning system."""

import esper
import pytest

from ninjamagic import bus
from ninjamagic.behavior import Attack, PathTowardEntity, SelectNearestAnchor, SelectNearestPlayer
from ninjamagic.component import BehaviorQueue, Glyph, Health, Noun, Stats, Transform
from ninjamagic.spawn import MOB_TEMPLATES, get_mob_strength, spawn_mob


@pytest.fixture(autouse=True)
def clear_esper():
    """Clear esper database before each test."""
    esper.clear_database()
    bus.clear()
    yield
    esper.clear_database()
    bus.clear()


class TestMobTemplates:
    """Tests for MOB_TEMPLATES."""

    def test_imp_template_exists(self):
        assert "imp" in MOB_TEMPLATES

    def test_wave_imp_template_exists(self):
        assert "wave_imp" in MOB_TEMPLATES

    def test_wolf_template_exists(self):
        assert "wolf" in MOB_TEMPLATES

    def test_templates_have_required_components(self):
        for name, template in MOB_TEMPLATES.items():
            assert "Noun" in template, f"{name} missing Noun"
            assert "Glyph" in template, f"{name} missing Glyph"
            assert "Health" in template, f"{name} missing Health"
            assert "BehaviorQueue" in template, f"{name} missing BehaviorQueue"


class TestSpawnMob:
    """Tests for spawn_mob function."""

    def test_spawn_creates_entity(self):
        map_id = esper.create_entity()

        mob_eid = spawn_mob("imp", map_id=map_id, y=10, x=20)

        assert esper.entity_exists(mob_eid)

    def test_spawn_adds_transform(self):
        map_id = esper.create_entity()

        mob_eid = spawn_mob("imp", map_id=map_id, y=10, x=20)

        assert esper.has_component(mob_eid, Transform)
        loc = esper.component_for_entity(mob_eid, Transform)
        assert loc.map_id == map_id
        assert loc.y == 10
        assert loc.x == 20

    def test_spawn_adds_noun(self):
        map_id = esper.create_entity()

        mob_eid = spawn_mob("imp", map_id=map_id, y=10, x=20)

        assert esper.has_component(mob_eid, Noun)
        noun = esper.component_for_entity(mob_eid, Noun)
        assert noun.value == "imp"

    def test_spawn_adds_glyph(self):
        map_id = esper.create_entity()

        mob_eid = spawn_mob("imp", map_id=map_id, y=10, x=20)

        assert esper.has_component(mob_eid, Glyph)

    def test_spawn_adds_health(self):
        map_id = esper.create_entity()

        mob_eid = spawn_mob("imp", map_id=map_id, y=10, x=20)

        assert esper.has_component(mob_eid, Health)
        health = esper.component_for_entity(mob_eid, Health)
        assert health.cur == 20.0

    def test_spawn_adds_stats(self):
        map_id = esper.create_entity()

        mob_eid = spawn_mob("imp", map_id=map_id, y=10, x=20)

        assert esper.has_component(mob_eid, Stats)
        stats = esper.component_for_entity(mob_eid, Stats)
        assert stats.grace == 5
        assert stats.grit == 3
        assert stats.wit == 2

    def test_spawn_adds_behavior_queue(self):
        map_id = esper.create_entity()

        mob_eid = spawn_mob("imp", map_id=map_id, y=10, x=20)

        assert esper.has_component(mob_eid, BehaviorQueue)
        queue = esper.component_for_entity(mob_eid, BehaviorQueue)
        assert len(queue.behaviors) == 3
        assert isinstance(queue.behaviors[0], SelectNearestPlayer)
        assert isinstance(queue.behaviors[1], PathTowardEntity)
        assert isinstance(queue.behaviors[2], Attack)

    def test_wave_imp_targets_anchors(self):
        map_id = esper.create_entity()

        mob_eid = spawn_mob("wave_imp", map_id=map_id, y=10, x=20)

        queue = esper.component_for_entity(mob_eid, BehaviorQueue)
        assert isinstance(queue.behaviors[0], SelectNearestAnchor)

    def test_spawn_unknown_template_raises(self):
        map_id = esper.create_entity()

        with pytest.raises(KeyError):
            spawn_mob("nonexistent_mob", map_id=map_id, y=10, x=20)


class TestGetMobStrength:
    """Tests for get_mob_strength function."""

    def test_imp_strength(self):
        # grace=5, grit=3, wit=2 = 10 + health 20/10 = 2 = 12
        assert get_mob_strength("imp") == 12

    def test_wolf_strength(self):
        # grace=8, grit=6, wit=4 = 18 + health 35/10 = 3 = 21
        assert get_mob_strength("wolf") == 21

    def test_unknown_template_returns_zero(self):
        assert get_mob_strength("nonexistent") == 0
