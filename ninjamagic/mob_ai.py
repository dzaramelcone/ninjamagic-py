"""Mob AI system."""

from collections.abc import Callable

from ninjamagic.behavior import assign_pack_leaders, process_all_behaviors


def process_mob_ai(*, walkable_check: Callable[[int, int], bool]) -> None:
    """Process AI for all mobs."""
    assign_pack_leaders()
    process_all_behaviors(walkable_check=walkable_check)
