from typing import Callable, Generator

import esper
from ninjamagic.component import EntityId, Noun, Transform, transform
from ninjamagic.util import VIEW_STRIDE

Reach = Callable[[Transform, Transform], bool]


def adjacent(this: Transform, that: Transform) -> bool:
    # symmetric, transitive, reflexive
    return this == that


def visible(this: Transform, that: Transform) -> bool:
    # symmetric, intransitive, reflexive
    return (
        this.map_id == that.map_id
        and abs(this.x - that.x) <= VIEW_STRIDE.width
        and abs(this.y - that.y) <= VIEW_STRIDE.height
    )


def find(
    source: EntityId, prefix: str, reach: Reach
) -> Generator[tuple[EntityId, Noun, Transform], None, None]:
    source_transform = transform(source)
    for other, (noun, other_transform) in esper.get_component(Noun, Transform):
        if other == source:
            continue
        if not noun.startswith(prefix):
            continue
        if not reach(other_transform, source_transform):
            continue
        yield other, noun, other_transform
