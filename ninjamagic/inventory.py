import logging
from typing import get_args

import esper
from pydantic import BaseModel

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
    Rotting,
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


class State(BaseModel):
    """Serializable state for item components that can change at runtime."""

    noun: Noun | None = None
    food: Food | None = None
    glyph: Glyph | None = None

    def components(self):
        """Yield non-None components for use as create_item overrides."""
        yield from (v for _, v in self if v)

    def model_dump_json(self, **kwargs) -> str:
        return super().model_dump_json(exclude_none=True, exclude_defaults=True, **kwargs)

    @classmethod
    def from_entity(cls, eid: int) -> "State":
        """Create State with components that differ from template."""
        key = esper.component_for_entity(eid, ItemKey).key
        template = ITEM_TYPES[key]
        kwargs = {}
        for name, field_info in cls.model_fields.items():
            component_type = next(a for a in get_args(field_info.annotation))
            cmp = esper.try_component(eid, component_type)
            if cmp != template.get(component_type):
                kwargs[name] = cmp
        return cls(**kwargs)


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




def create_item(
    key: str,
    *overrides: object,
    transform: Transform,
    level: int,
    contained_by: int = 0,
    slot: Slot = Slot.ANY,
) -> int:
    """Create an esper entity from an item template.

    Required: transform, level (all items need position and level).
    Optional: contained_by (default 0), slot (default ANY).
    Overrides: replace template components.
    """
    template = ITEM_TYPES[key]
    entity = esper.create_entity(transform, slot, *template.values(), *overrides)
    esper.add_component(entity, level, Level)
    esper.add_component(entity, contained_by, ContainedBy)
    return entity




async def load_player_inventory(q: AsyncQuerier, owner_id: int, entity_id: int) -> None:
    """Load player inventory from the database."""
    inventories = [row async for row in q.get_inventories_for_owner(owner_id=owner_id)]
    log.info("load_player_inventory owner_id=%d: %d items", owner_id, len(inventories))
    if not inventories:
        return

    # First pass: create all entities with contained_by=0
    entity_by_eid: dict[int, int] = {}
    for inv in inventories:
        log.debug(
            "  loading item: %s (eid=%d, container_eid=%s, slot=%s state=%s)",
            inv.key, inv.eid, inv.container_eid, inv.slot, inv.state
        )
        parsed = State.model_validate(inv.state or {})
        entity = create_item(
            inv.key,
            *parsed.components(),
            transform=Transform(map_id=0, y=0, x=0),
            level=inv.level,
            slot=Slot(inv.slot),
        )
        entity_by_eid[inv.eid] = entity

    for inv in inventories:
        entity = entity_by_eid[inv.eid]
        container = entity_by_eid[inv.container_eid] if inv.container_eid else entity_id
        log.debug(
            "  containment: %s (entity=%d) -> container entity=%d",
            inv.key, entity, container
        )
        esper.add_component(entity, container, ContainedBy)


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
                state=State.from_entity(entity).model_dump_json(),
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
            state=State.from_entity(entity).model_dump_json(),
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
                state=State.from_entity(entity).model_dump_json(),
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
    # Load all world items (owner_id IS NULL), including nested container contents
    inventories = [row async for row in q.get_world_inventories()]
    # Filter to items on loaded maps (root items or nested in containers on those maps)
    root_eids = {inv.eid for inv in inventories if inv.map_id in map_ids}
    # BFS to find all nested items
    all_eids = set(root_eids)
    queue = list(root_eids)
    while queue:
        parent_eid = queue.pop()
        for inv in inventories:
            if inv.container_eid == parent_eid and inv.eid not in all_eids:
                all_eids.add(inv.eid)
                queue.append(inv.eid)
    inventories = [inv for inv in inventories if inv.eid in all_eids]
    log.info("load_map_inventory loaded %d items", len(inventories))
    if not inventories:
        return

    # First pass: create all entities with contained_by=0
    entity_by_eid: dict[int, int] = {}
    for inv in inventories:
        # Root items have world position, contained items have (0,0,0)
        transform = Transform(map_id=0, y=0, x=0)
        if not inv.container_eid:
            transform = Transform(map_id=inv.map_id, y=inv.y, x=inv.x)
        parsed = State.model_validate(inv.state or {})
        entity = create_item(
            inv.key,
            *parsed.components(),
            transform=transform,
            level=inv.level,
            slot=Slot(inv.slot),
        )
        entity_by_eid[inv.eid] = entity

    # Second pass: set up containment for contained items
    for inv in inventories:
        if inv.container_eid:
            entity = entity_by_eid[inv.eid]
            esper.add_component(entity, entity_by_eid[inv.container_eid], ContainedBy)

# Item templates keyed by item type string.
# Each value is a dict mapping component type -> component instance.
# All components should be frozen dataclasses with eq=True.
ITEM_TYPES: dict[str, dict[type, object]] = {
    "scenery": {
        ItemKey: ItemKey(key="scenery"),
        Noun: Noun(value="scenery", num=2),
        Glyph: Glyph(char="ო", h=0.33, s=0.6, v=0.6),
    },
    "prop": {
        ItemKey: ItemKey(key="prop"),
        Noun: Noun(value="prop"),
        Glyph: Glyph(char="?", h=0.0, s=0.0, v=0.7),
    },
    "torch": {
        ItemKey: ItemKey(key="torch"),
        Noun: Noun(value="torch"),
        Glyph: Glyph(char="!", h=0.1, s=0.8, v=0.9),
        ProvidesLight: ProvidesLight(),
    },
    "bonfire": {
        ItemKey: ItemKey(key="bonfire"),
        Noun: Noun(value="bonfire"),
        Glyph: Glyph(char="⚶", h=0.95, s=0.6, v=0.65),
        ProvidesHeat: ProvidesHeat(),
        ProvidesLight: ProvidesLight(),
        Anchor: Anchor(rank=1, tnl=0, rankup_echo="{0:def} {0:flares}, casting back the darkness."),
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
    "bedroll": {
        ItemKey: ItemKey(key="bedroll"),
        Noun: Noun(adjective="leather", value="bedroll"),
        Glyph: Glyph(char="=", h=0.1, s=0.4, v=0.5),
        ProvidesShelter: ProvidesShelter(prompt="settle into bedroll"),
    },
    "cookpot": {
        ItemKey: ItemKey(key="cookpot"),
        Noun: Noun(adjective="crude", value="cookpot"),
        Glyph: Glyph(char="u", h=0.08, s=0.3, v=0.4),
        Container: Container(),
        Cookware: Cookware(),
    },
    "meal": {
        ItemKey: ItemKey(key="meal"),
        Noun: Noun(value="meal"),
        Glyph: Glyph(char="ʘ", h=0.33, s=0.65, v=0.55),
        Food: Food(count=1),
        Rotting: Rotting(),
    },
    "forage": {
        ItemKey: ItemKey(key="forage"),
        Noun: Noun(value="forage", num=2),
        Glyph: Glyph(char="♣", h=0.33, s=0.65, v=0.55),
        Ingredient: Ingredient(),
    },
    "corpse": {
        ItemKey: ItemKey(key="corpse"),
        Noun: Noun(value="corpse"),
        Glyph: Glyph(char="%", h=0.0, s=0.0, v=0.4),
        Rotting: Rotting(),
        DoNotSave: DoNotSave(),
    },
}