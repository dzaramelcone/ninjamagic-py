from collections.abc import Callable, Generator
from typing import Any

import esper

from ninjamagic.component import EntityId, Noun, Transform, transform
from ninjamagic.util import VIEW_STRIDE_H, VIEW_STRIDE_W

Selector = Callable[[Transform, Transform], bool]


def find_at[T](position: Transform, component: type[T]) -> tuple[EntityId, T] | None:
    """Find first entity at position with given component."""
    for eid, (tf, cmp) in esper.get_components(Transform, component):
        if tf == position:
            return eid, cmp
    return None


def adjacent(this: Transform, that: Transform) -> bool:
    # symmetric, transitive, reflexive
    return this == that


def visible(this: Transform, that: Transform) -> bool:
    # symmetric, intransitive, reflexive
    return (
        this.map_id == that.map_id
        and abs(this.x - that.x) <= VIEW_STRIDE_W
        and abs(this.y - that.y) <= VIEW_STRIDE_H
    )


def world(this: Transform, that: Transform) -> bool:
    return True


def find(
    source: EntityId,
    prefix: str,
    in_range: Selector,
    *,
    with_components: tuple[type[Any], ...] = (),
) -> Generator[tuple[EntityId, Noun, Transform]]:
    source_transform = transform(source)
    for other, cmps in esper.get_components(Noun, Transform, *with_components):
        noun, other_transform = cmps[0], cmps[1]
        if other == source:
            continue
        if not in_range(other_transform, source_transform):
            continue
        if not noun.matches(prefix):
            continue
        yield other, noun, other_transform


def find_one(
    source: EntityId,
    prefix: str,
    in_range: Selector,
    *,
    with_components: tuple[type[Any], ...] = (),
) -> tuple[EntityId, Noun, Transform] | None:
    """Find first matching entity or None."""
    return next(find(source, prefix, in_range, with_components=with_components), None)
