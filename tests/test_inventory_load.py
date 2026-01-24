import esper

from ninjamagic.component import ItemKey, Noun, ProvidesLight, Transform
from ninjamagic.inventory import ITEM_TYPES, create_item


def test_item_key_component_exists():
    key = ItemKey(key="torch")
    assert key.key == "torch"


def test_item_factory_creates_entity_with_components():
    eid = create_item("torch", transform=Transform(map_id=0, y=0, x=0), level=0)
    assert eid != 0
    # Check components from ITEM_TYPES["torch"] were added
    item_key = esper.component_for_entity(eid, ItemKey)
    assert item_key.key == "torch"
    noun = esper.component_for_entity(eid, Noun)
    assert noun.value == "torch"
    assert esper.has_component(eid, ProvidesLight)


def test_item_types_has_expected_items():
    assert "torch" in ITEM_TYPES
    assert "broadsword" in ITEM_TYPES
    assert "backpack" in ITEM_TYPES
    assert "bonfire" in ITEM_TYPES
    assert "forage" in ITEM_TYPES
