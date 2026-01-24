from ninjamagic.armor import mitigate
from ninjamagic.component import Armor, Level


def test_mitigate_uses_level_component():
    armor = Armor(skill_key="martial_arts", physical_immunity=0.4, magical_immunity=0.0)
    lvl = Level(10)
    out = mitigate(defend_ranks=5, attack_ranks=5, armor=armor, item_level=lvl)
    assert 0.0 < out < 1.0
