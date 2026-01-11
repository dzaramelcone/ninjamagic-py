# tests/test_spawn.py
from ninjamagic.spawn import find_spawn_point


def test_find_spawn_point_avoids_anchors():
    """Spawn points are outside anchor radii."""
    # Anchor at (50, 50) with radius 24
    anchors = [(50, 50, 24.0)]

    # Should find a point outside the radius
    point = find_spawn_point(
        map_id=1,
        anchors=anchors,
        min_distance=30,
        max_distance=50,
        walkable_check=lambda y, x: True,  # All walkable for test
    )

    assert point is not None
    y, x = point

    # Verify it's outside anchor radius
    import math

    dist = math.sqrt((y - 50) ** 2 + (x - 50) ** 2)
    assert dist >= 24


def test_find_spawn_point_respects_walkable():
    """Spawn points must be on walkable tiles."""
    anchors = [(50, 50, 24.0)]

    # Nothing walkable = no spawn point
    point = find_spawn_point(
        map_id=1,
        anchors=anchors,
        min_distance=30,
        max_distance=50,
        walkable_check=lambda y, x: False,
    )

    assert point is None


def test_create_mob():
    """Create a mob entity with all required components."""
    import esper

    from ninjamagic.component import Health, Mob, MobType, Noun, Skills, Stance, Transform
    from ninjamagic.spawn import create_mob

    esper.clear_database()

    eid = create_mob(
        mob_type=MobType.SWARM,
        map_id=1,
        y=10,
        x=20,
        name="goblin",
    )

    # Verify all components
    assert esper.has_component(eid, Mob)
    assert esper.has_component(eid, Transform)
    assert esper.has_component(eid, Health)
    assert esper.has_component(eid, Noun)
    assert esper.has_component(eid, Stance)
    assert esper.has_component(eid, Skills)

    mob = esper.component_for_entity(eid, Mob)
    assert mob.mob_type == MobType.SWARM

    transform = esper.component_for_entity(eid, Transform)
    assert transform.map_id == 1
    assert transform.y == 10
    assert transform.x == 20


def test_spawn_processor():
    """Spawn processor creates mobs over time."""
    import esper

    from ninjamagic.component import Anchor, Mob, Transform
    from ninjamagic.spawn import SpawnConfig, process_spawning

    esper.clear_database()

    # Create a map
    map_id = esper.create_entity()

    # Create an anchor
    anchor_eid = esper.create_entity()
    esper.add_component(anchor_eid, Transform(map_id=map_id, y=50, x=50))
    esper.add_component(anchor_eid, Anchor(strength=1.0, fuel=100.0))

    # Configure spawning
    config = SpawnConfig(
        spawn_rate=1.0,  # 1 mob per second
        max_mobs=10,
        min_distance=30,
        max_distance=50,
    )

    # Process spawning for 2 seconds
    def walkable(y: int, x: int) -> bool:
        return True

    process_spawning(
        map_id=map_id,
        delta_seconds=2.0,
        config=config,
        walkable_check=walkable,
    )

    # Should have spawned some mobs
    mob_count = len(list(esper.get_component(Mob)))
    assert mob_count >= 1
