import logging

import esper
from pydantic import BaseModel, TypeAdapter

from ninjamagic.component import (
    Anchor,
    Chips,
    ContainedBy,
    Container,
    Cookware,
    DoNotSave,
    Food,
    Glyph,
    Ingredient,
    ItemKey,
    Level,
    Noun,
    ProvidesHeat,
    ProvidesLight,
    ProvidesShelter,
    Slot,
    Transform,
    Weapon,
    Wearable,
)
from ninjamagic.gen.query import (
    AsyncQuerier,
    ReplaceInventoriesForMapParams,
    ReplaceInventoriesForOwnerParams,
)

log = logging.getLogger(__name__)

# Components that can be serialized to/from state JSON.
# Only include components that can change at runtime.
# Weapon is not here because it never changes.
STATE_TYPES: list[type] = [Noun]
STATE_ADAPTERS: dict[str, TypeAdapter] = {cls.__name__: TypeAdapter(cls) for cls in STATE_TYPES}


class InventoryRow(BaseModel):
    """One row of inventory data for persistence."""

    eid: int
    key: str
    slot: str
    container_eid: int = 0  # 0 → NULL in SQL
    map_id: int = -1  # -1 → NULL in SQL
    x: int = -1
    y: int = -1
    state: object | None
    level: int
    owner_id: int = 0


# Item templates keyed by item type string.
# Each value is a dict mapping component type -> component instance.
# All components should be frozen dataclasses with eq=True.
ITEM_TYPES: dict[str, dict[type, object]] = {
    "torch": {
        ItemKey: ItemKey(key="torch"),
        Noun: Noun(value="torch"),
        Glyph: Glyph(char="!", h=0.1, s=0.8, v=0.9),
        ProvidesLight: ProvidesLight(),
    },
    "bonfire": {
        ItemKey: ItemKey(key="bonfire"),
        Noun: Noun(value="bonfire"),
        Glyph: Glyph(char="⚶", h=0.05, s=0.9, v=1.0),
        ProvidesHeat: ProvidesHeat(),
        ProvidesLight: ProvidesLight(),
        Anchor: Anchor(rank=1, tnl=0, rankup_echo="The bonfire crackles warmly."),
    },
    "broadsword": {
        ItemKey: ItemKey(key="broadsword"),
        Noun: Noun(value="broadsword"),
        Glyph: Glyph(char="/", h=0.0, s=0.1, v=0.8),
        Weapon: Weapon(damage=15.0, token_key="slash", story_key="blade", skill_key="martial_arts"),
    },
    "backpack": {
        ItemKey: ItemKey(key="backpack"),
        Noun: Noun(value="backpack"),
        Glyph: Glyph(char="(", h=0.08, s=0.5, v=0.5),
        Container: Container(),
        Wearable: Wearable(slot=Slot.BACK),
    },
    "leek": {
        ItemKey: ItemKey(key="leek"),
        Noun: Noun(value="leek"),
        Glyph: Glyph(char="%", h=0.33, s=0.7, v=0.7),
        Ingredient: Ingredient(),
        Food: Food(count=1),
    },
    "lily_pad": {
        ItemKey: ItemKey(key="lily_pad"),
        Noun: Noun(value="lily pad"),
        Glyph: Glyph(char="ო", h=0.33, s=0.6, v=0.6),
    },
    "cookpot": {
        ItemKey: ItemKey(key="cookpot"),
        Noun: Noun(adjective="crude", value="cookpot"),
        Glyph: Glyph(char="u", h=0.08, s=0.3, v=0.4),
        Container: Container(),
        Cookware: Cookware(),
    },
    "bedroll": {
        ItemKey: ItemKey(key="bedroll"),
        Noun: Noun(adjective="leather", value="bedroll"),
        Glyph: Glyph(char="=", h=0.1, s=0.4, v=0.5),
        ProvidesShelter: ProvidesShelter(prompt="settle into bedroll"),
    },
}


def create_item(key: str) -> int:
    """Create an esper entity from an item template."""
    template = ITEM_TYPES[key]
    entity = esper.create_entity()
    for comp_type, comp_value in template.items():
        esper.add_component(entity, comp_value, comp_type)
    return entity


def load_state(state: list[dict] | None) -> list[object]:
    """Deserialize state JSON into component instances."""

    if not state:
        return []
    return [STATE_ADAPTERS[entry["kind"]].validate_python(entry) for entry in state]


def dump_state(eid: int, item_key: str) -> list[dict] | None:
    """Serialize only components that differ from the template."""

    template = ITEM_TYPES[item_key]
    return [
        STATE_ADAPTERS[type(comp).__name__].dump_python(comp)
        for cls in STATE_TYPES
        if (comp := esper.try_component(eid, cls)) and comp != template.get(cls)
    ] or None



async def load_player_inventory(q: AsyncQuerier, owner_id: int, entity_id: int) -> None:
    """Load player inventory from the database."""
    inventories = [row async for row in q.get_inventories_for_owner(owner_id=owner_id)]
    log.info("load_player_inventory owner_id=%d: %d items", owner_id, len(inventories))
    if not inventories:
        return

    entity_by_eid: dict[int, int] = {}
    for inv in inventories:
        log.debug(
            "  loading item: %s (eid=%d, container_eid=%s, slot=%s)",
            inv.key, inv.eid, inv.container_eid, inv.slot
        )
        entity = create_item(inv.key)
        esper.add_component(entity, inv.level, Level)
        for comp in load_state(inv.state):
            esper.add_component(entity, comp)
        entity_by_eid[inv.eid] = entity

    # Second pass: set up containment and transform
    for inv in inventories:
        entity = entity_by_eid[inv.eid]
        container = entity_by_eid[inv.container_eid] if inv.container_eid else entity_id
        log.debug(
            "  containment: %s (entity=%d) -> container entity=%d",
            inv.key, entity, container
        )
        esper.add_component(entity, container, ContainedBy)
        esper.add_component(entity, Slot(inv.slot))
        esper.add_component(entity, Transform(map_id=0, y=0, x=0))


async def save_player_inventory(q: AsyncQuerier, owner_id: int, owner_entity: int) -> None:
    """Save player inventory to the database."""
    log.info("save_player_inventory owner_id=%d entity=%d", owner_id, owner_entity)
    # Collect all items contained by owner (recursively through containers)
    queue = [owner_entity]
    seen = {owner_entity}
    rows: list[InventoryRow] = []
    entity_to_eid: dict[int, int] = {}
    next_eid = 1

    while queue:
        container = queue.pop()
        for entity, (item_key, loc, slot) in esper.get_components(ItemKey, ContainedBy, Slot):
            if loc != container or entity in seen:
                continue
            if esper.has_component(entity, DoNotSave):
                continue

            seen.add(entity)
            container_eid = entity_to_eid.get(loc, 0)
            log.debug(
                "  saving item: %s (entity=%d) in container_eid=%d, slot=%s",
                item_key.key, entity, container_eid, slot
            )
            rows.append(InventoryRow(
                eid=next_eid,
                key=item_key.key,
                slot=slot,
                container_eid=container_eid,
                state=dump_state(entity, item_key.key),
                level=esper.try_component(entity, Level) or 0,
                owner_id=owner_id,
            ))
            entity_to_eid[entity] = next_eid
            next_eid += 1
            if esper.has_component(entity, Container):
                log.debug("    -> has Container, will search its contents")
                queue.append(entity)

    log.info("save_player_inventory owner_id=%d: %d items", owner_id, len(rows))
    await q.replace_inventories_for_owner(
        ReplaceInventoriesForOwnerParams(
            owner_id=owner_id,
            eids=[r.eid for r in rows],
            owner_ids=[r.owner_id for r in rows],
            keys=[r.key for r in rows],
            slots=[r.slot for r in rows],
            container_eids=[r.container_eid for r in rows],
            map_ids=[r.map_id for r in rows],
            xs=[r.x for r in rows],
            ys=[r.y for r in rows],
            states=[r.state for r in rows],
            levels=[r.level for r in rows],
        )
    )


async def save_map_inventory(q: AsyncQuerier, map_id: int) -> None:
    """Save world-space inventory for a map to the database."""
    log.info("save_map_inventory map_id=%d", map_id)

    # Find root items on this map (have Transform, not inside a container)
    roots = [
        (entity, item_key, transform)
        for entity, (item_key, transform) in esper.get_components(ItemKey, Transform)
        if transform.map_id == map_id
        and not esper.has_component(entity, DoNotSave)
        and not esper.try_component(entity, ContainedBy)
    ]

    rows: list[InventoryRow] = []
    entity_to_eid: dict[int, int] = {}
    queue: list[int] = []
    seen: set[int] = set()
    next_eid = 1

    # First pass: save root items with Transform
    for entity, item_key, transform in roots:
        seen.add(entity)
        rows.append(InventoryRow(
            eid=next_eid,
            key=item_key.key,
            slot="",
            container_eid=0,
            map_id=transform.map_id,
            x=transform.x,
            y=transform.y,
            state=dump_state(entity, item_key.key),
            level=esper.try_component(entity, Level) or 0,
        ))
        entity_to_eid[entity] = next_eid
        next_eid += 1
        if esper.has_component(entity, Container):
            queue.append(entity)

    # BFS: traverse container contents
    while queue:
        container = queue.pop()
        for entity, (item_key, loc, slot) in esper.get_components(ItemKey, ContainedBy, Slot):
            if loc != container or entity in seen:
                continue
            if esper.has_component(entity, DoNotSave):
                continue

            seen.add(entity)
            rows.append(InventoryRow(
                eid=next_eid,
                key=item_key.key,
                slot=slot,
                container_eid=entity_to_eid[loc],
                state=dump_state(entity, item_key.key),
                level=esper.try_component(entity, Level) or 0,
            ))
            entity_to_eid[entity] = next_eid
            next_eid += 1
            if esper.has_component(entity, Container):
                queue.append(entity)

    log.info("save_map_inventory map_id=%d: %d items", map_id, len(rows))

    await q.replace_inventories_for_map(
        ReplaceInventoriesForMapParams(
            map_id=map_id,
            eids=[r.eid for r in rows],
            keys=[r.key for r in rows],
            slots=[r.slot for r in rows],
            container_eids=[r.container_eid for r in rows],
            map_ids=[r.map_id for r in rows],
            xs=[r.x for r in rows],
            ys=[r.y for r in rows],
            states=[r.state for r in rows],
            levels=[r.level for r in rows],
        )
    )

async def load_map_inventory(q: AsyncQuerier) -> None:
    """Load world items from the database."""
    map_ids = {eid for eid, _ in esper.get_component(Chips)}
    log.info("load_map_inventory map_ids=%s", map_ids)
    inventories = []
    for map_id in map_ids:
        inventories.extend([row async for row in q.get_inventories_for_map(map_id=map_id)])
    log.info("load_map_inventory loaded %d items", len(inventories))
    if not inventories:
        return

    entity_by_eid: dict[int, int] = {}
    for inv in inventories:
        entity = create_item(inv.key)
        esper.add_component(entity, inv.level, Level)
        for comp in load_state(inv.state):
            esper.add_component(entity, comp)
        entity_by_eid[inv.eid] = entity

    # Second pass: set up containment and transforms
    for inv in inventories:
        entity = entity_by_eid[inv.eid]
        if inv.container_eid:
            esper.add_component(entity, entity_by_eid[inv.container_eid], ContainedBy)
            esper.add_component(entity, Slot(inv.slot))
        elif inv.map_id:
            esper.add_component(entity, Transform(map_id=inv.map_id, x=inv.x, y=inv.y))
            esper.add_component(entity, 0, ContainedBy)
            esper.add_component(entity, Slot(inv.slot))
