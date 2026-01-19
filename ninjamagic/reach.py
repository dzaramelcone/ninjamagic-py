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


def chebyshev(
    h: int, w: int, m1: int, y1: int, x1: int, m2: int, y2: int, x2: int
) -> bool:
    """Chebyshev distance check with raw coordinates."""
    return m1 == m2 and abs(y1 - y2) <= h and abs(x1 - x2) <= w


def chebyshev_tf(h: int, w: int) -> Selector:
    """DEPRECATED: Transform-based selector. Use chebyshev() with raw coords instead."""

    def check(this: Transform, that: Transform) -> bool:
        return chebyshev(
            h, w, this.map_id, this.y, this.x, that.map_id, that.y, that.x
        )

    return check


visible = chebyshev_tf(VIEW_STRIDE_H, VIEW_STRIDE_W)


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
    if not prefix:
        return None
    return next(find(source, prefix, in_range, with_components=with_components), None)
