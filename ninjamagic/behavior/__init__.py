"""Mob behavior system."""

from collections.abc import Callable

from ninjamagic.behavior.boss import process_boss
from ninjamagic.behavior.death_knight import process_death_knight
from ninjamagic.behavior.pack import assign_pack_leaders as assign_pack_leaders, process_pack
from ninjamagic.behavior.swarm import process_swarm


def process_all_behaviors(
    *,
    walkable_check: Callable[[int, int], bool],
) -> None:
    """Process behavior for all mob types."""
    process_swarm(walkable_check=walkable_check)
    process_pack(walkable_check=walkable_check)
    process_death_knight(walkable_check=walkable_check)
    process_boss(walkable_check=walkable_check)
