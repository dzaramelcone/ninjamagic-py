import esper

from ninjamagic.component import Transform
from ninjamagic.inventory import create_item, State


def test_serialize_state_returns_empty_json_when_unchanged():
    # Create an entity without modifying anything
    eid = create_item("torch", transform=Transform(map_id=0, y=0, x=0), level=0)

    # Serialize state - should be empty JSON object since nothing changed
    state = State.from_entity(eid).model_dump_json()
    assert state == "{}"
