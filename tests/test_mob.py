# tests/test_mob.py
from ninjamagic.component import Mob, MobType


def test_mob_component():
    """Mobs have type and behavior properties."""
    mob = Mob(mob_type=MobType.SWARM, aggro_range=8)

    assert mob.mob_type == MobType.SWARM
    assert mob.aggro_range == 8


def test_mob_defaults():
    """Mobs have sensible defaults."""
    mob = Mob()

    assert mob.mob_type == MobType.SWARM
    assert mob.aggro_range == 6
    assert mob.target is None


def test_mob_behavior_component():
    """Mobs have behavior state."""
    from ninjamagic.component import BehaviorState, MobBehavior

    behavior = MobBehavior(
        state=BehaviorState.IDLE,
        target_entity=None,
        cooldown=0.0,
    )

    assert behavior.state == BehaviorState.IDLE
    assert behavior.target_entity is None
    assert behavior.cooldown == 0.0
    assert behavior.pack_leader is None
