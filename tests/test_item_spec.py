from ninjamagic.component import Noun, Weapon
from ninjamagic.item_spec import dump_item_spec, load_item_spec


def test_item_spec_roundtrip():
    spec = dump_item_spec([Noun(value="sword"), Weapon(damage=12.0)])
    comps = load_item_spec(spec)
    assert any(isinstance(c, Noun) and c.value == "sword" for c in comps)
    assert any(isinstance(c, Weapon) and c.damage == 12.0 for c in comps)
