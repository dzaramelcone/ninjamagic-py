import esper

from ninjamagic.component import ItemKey, Noun, ProvidesLight
from ninjamagic.inventory import ITEM_TYPES, item_factory


def test_item_key_component_exists():
    key = ItemKey(key="torch")
    assert key.key == "torch"


def test_item_factory_creates_entity_with_components():
    eid = item_factory("torch")
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
    assert "leek" in ITEM_TYPES
