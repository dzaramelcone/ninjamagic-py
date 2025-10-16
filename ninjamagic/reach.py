from collections.abc import Callable, Generator

import esper

from ninjamagic.component import EntityId, Noun, Transform, transform
from ninjamagic.util import VIEW_STRIDE

Selector = Callable[[Transform, Transform], bool]


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
    source: EntityId, prefix: str, range: Selector
) -> Generator[tuple[EntityId, Noun, Transform]]:
    source_transform = transform(source)
    for other, (noun, other_transform) in esper.get_components(Noun, Transform):
        if other == source:
            continue
        if not range(other_transform, source_transform):
            continue
        if not noun.lower().startswith(prefix):
            continue
        yield other, noun, other_transform
