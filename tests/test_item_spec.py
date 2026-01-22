import esper

from ninjamagic.component import Noun
from ninjamagic.inventory import load_state, create_item, dump_state


def test_state_roundtrip():
    # Create an entity and modify a stateful component
    eid = create_item("torch")

    # Modify the Noun component
    modified_noun = Noun(value="dead torch")
    esper.add_component(eid, modified_noun)

    # Serialize state - should only include the modified Noun
    state = dump_state(eid, "torch")
    assert state is not None
    assert len(state) == 1
    assert state[0]["kind"] == "Noun"
    assert state[0]["value"] == "dead torch"

    # Deserialize and verify
    comps = load_state(state)
    assert len(comps) == 1
    assert isinstance(comps[0], Noun)
    assert comps[0].value == "dead torch"


def test_serialize_state_returns_none_when_unchanged():
    # Create an entity without modifying anything
    eid = create_item("torch")

    # Serialize state - should be None since nothing changed
    state = dump_state(eid, "torch")
    assert state is None
