"""Mob spawning system: spawn from darkness, path toward light.

Mobs spawn from unlit tiles (outside anchor radius) during night phases.
Wave mobs specifically target anchors during wave hours.
"""

import esper

from ninjamagic.behavior import (
    Attack,
    FleeFromEntity,
    PathTowardEntity,
    SelectNearestAnchor,
    SelectNearestPlayer,
    Wait,
)
from ninjamagic.component import (
    BehaviorQueue,
    EntityId,
    Glyph,
    Health,
    Noun,
    Pronouns,
    Stats,
    Transform,
)

# Mob templates define components to add when spawning
# Each key is a component class name, value is kwargs for that component
MOB_TEMPLATES: dict[str, dict] = {
    "imp": {
        "Noun": {"value": "imp", "pronoun": Pronouns.IT},
        "Glyph": ("i", 0.8, 0.2, 0.2),  # red
        "Health": {"cur": 20.0},
        "Stats": {"grace": 5, "grit": 3, "wit": 2},
        "BehaviorQueue": {
            "behaviors": [
                SelectNearestPlayer(),
                PathTowardEntity(),
                Attack(),
            ]
        },
    },
    "wave_imp": {
        "Noun": {"value": "imp", "pronoun": Pronouns.IT},
        "Glyph": ("i", 0.0, 0.8, 0.5),  # dark purple
        "Health": {"cur": 15.0},
        "Stats": {"grace": 4, "grit": 2, "wit": 1},
        "BehaviorQueue": {
            "behaviors": [
                SelectNearestAnchor(),
                PathTowardEntity(),
                Attack(),
            ]
        },
    },
    "wolf": {
        "Noun": {"value": "wolf", "pronoun": Pronouns.IT},
        "Glyph": ("w", 0.1, 0.3, 0.4),  # gray
        "Health": {"cur": 35.0},
        "Stats": {"grace": 8, "grit": 6, "wit": 4},
        "BehaviorQueue": {
            "behaviors": [
                SelectNearestPlayer(),
                PathTowardEntity(),
                Attack(),
            ]
        },
    },
    "coward_rat": {
        "Noun": {"value": "rat", "pronoun": Pronouns.IT},
        "Glyph": ("r", 0.08, 0.3, 0.5),  # brown
        "Health": {"cur": 8.0},
        "Stats": {"grace": 10, "grit": 1, "wit": 3},
        "BehaviorQueue": {
            "behaviors": [
                SelectNearestPlayer(),
                FleeFromEntity(),  # Runs from players
                Wait(),
            ]
        },
    },
}


def spawn_mob(
    template_name: str,
    *,
    map_id: EntityId,
    y: int,
    x: int,
) -> EntityId:
    """Spawn a mob from a template at the given position.

    Args:
        template_name: Key in MOB_TEMPLATES
        map_id: Map entity ID
        y: Y position
        x: X position

    Returns:
        Entity ID of the spawned mob

    Raises:
        KeyError: If template_name is not in MOB_TEMPLATES
    """
    template = MOB_TEMPLATES[template_name]
    eid = esper.create_entity()

    # Add Transform
    esper.add_component(eid, Transform(map_id=map_id, y=y, x=x))

    # Add components from template
    for comp_name, value in template.items():
        match comp_name:
            case "Noun":
                esper.add_component(eid, Noun(**value))
            case "Glyph":
                # Glyph is a tuple, not a dataclass
                esper.add_component(eid, value, Glyph)
            case "Health":
                esper.add_component(eid, Health(**value))
            case "Stats":
                esper.add_component(eid, Stats(**value))
            case "BehaviorQueue":
                esper.add_component(eid, BehaviorQueue(**value))

    return eid


def get_mob_strength(template_name: str) -> int:
    """Get the effective strength of a mob template for anchor contests.

    Strength is based on stats and health.
    """
    template = MOB_TEMPLATES.get(template_name, {})
    stats = template.get("Stats", {})
    health = template.get("Health", {})

    # Base strength from stats
    grace = stats.get("grace", 0)
    grit = stats.get("grit", 0)
    wit = stats.get("wit", 0)
    stat_total = grace + grit + wit

    # Bonus from health
    health_bonus = int(health.get("cur", 0) / 10)

    return stat_total + health_bonus
