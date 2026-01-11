# tests/test_mob.py
import pytest
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
