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
)
from ninjamagic.gen.query import (
    AsyncQuerier,
    ReplaceInventoriesForMapParams,
    ReplaceInventoriesForOwnerParams,
)

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
        ProvidesLight: ProvidesLight(),
    },
    "bonfire": {
        ItemKey: ItemKey(key="bonfire"),
        Noun: Noun(value="bonfire"),
        ProvidesHeat: ProvidesHeat(),
        ProvidesLight: ProvidesLight(),
        Anchor: Anchor(rank=1, tnl=0, rankup_echo="The bonfire crackles warmly."),
    },
    "broadsword": {
        ItemKey: ItemKey(key="broadsword"),
        Noun: Noun(value="broadsword"),
        Weapon: Weapon(damage=15.0, token_key="slash", story_key="blade", skill_key="martial_arts"),
    },
    "backpack": {
        ItemKey: ItemKey(key="backpack"),
        Noun: Noun(value="backpack"),
        Container: Container(),
    },
    "leek": {
        ItemKey: ItemKey(key="leek"),
        Noun: Noun(value="leek"),
        Ingredient: Ingredient(),
        Food: Food(count=1),
    },
    "lily_pad": {
        ItemKey: ItemKey(key="lily_pad"),
        Noun: Noun(value="lily pad"),
    },
    "cookpot": {
        ItemKey: ItemKey(key="cookpot"),
        Noun: Noun(adjective="crude", value="cookpot"),
        Container: Container(),
        Cookware: Cookware(),
    },
    "bedroll": {
        ItemKey: ItemKey(key="bedroll"),
        Noun: Noun(adjective="leather", value="bedroll"),
        ProvidesShelter: ProvidesShelter(prompt="settle into bedroll"),
    },
}


def create_item(key: str) -> int:
    """Create an esper entity from an item template."""
    return esper.create_entity(*ITEM_TYPES[key].values())


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
    if not inventories:
        return

    entity_by_eid: dict[int, int] = {}
    for inv in inventories:
        entity = create_item(inv.key)
        esper.add_component(entity, inv.level, Level)
        for comp in load_state(inv.state):
            esper.add_component(entity, comp)
        entity_by_eid[inv.eid] = entity

    # Second pass: set up containment
    for inv in inventories:
        entity = entity_by_eid[inv.eid]
        container = entity_by_eid[inv.container_eid] if inv.container_eid else entity_id
        esper.add_component(entity, container, ContainedBy)
        esper.add_component(entity, Slot(inv.slot))


async def save_player_inventory(q: AsyncQuerier, owner_id: int, owner_entity: int) -> None:
    """Save player inventory to the database."""
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
            rows.append(InventoryRow(
                eid=next_eid,
                key=item_key.key,
                slot=slot,
                container_eid=entity_to_eid.get(loc, 0),
                state=dump_state(entity, item_key.key),
                level=esper.try_component(entity, Level) or 0,
                owner_id=owner_id,
            ))
            entity_to_eid[entity] = next_eid
            next_eid += 1
            if esper.has_component(entity, Container):
                queue.append(entity)

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
    rows = [
        InventoryRow(
            eid=idx,
            key=item_key.key,
            slot="",
            container_eid=0,
            map_id=transform.map_id,
            x=transform.x,
            y=transform.y,
            state=dump_state(entity, item_key.key),
            level=esper.try_component(entity, Level) or 0,
        )
        for idx, (entity, item_key, transform) in enumerate(
            (
                (entity, item_key, transform)
                for entity, (item_key, transform) in esper.get_components(ItemKey, Transform)
                if transform.map_id == map_id and not esper.has_component(entity, DoNotSave)
            ),
            start=1,
        )
    ]

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
    inventories = []
    for map_id in map_ids:
        inventories.extend([row async for row in q.get_inventories_for_map(map_id=map_id)])
    if not inventories:
        return

    entity_by_eid: dict[int, int] = {}
    for inv in inventories:
        entity = create_item(inv.key)
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

