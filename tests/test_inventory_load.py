from ninjamagic.component import ItemKey
from ninjamagic.inventory import hydrate_item_entity


def test_item_key_component_exists():
    assert ItemKey("torch")


def test_hydrate_item_sets_components():
    entity = hydrate_item_entity(template_name="torch", spec=[{"kind": "Noun", "value": "torch"}])
    assert entity != 0
