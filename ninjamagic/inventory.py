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

    id: int
    key: str
    slot: str
    container_id: int
    map_id: int
    x: int
    y: int
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


def item_factory(key: str) -> int:
    """Create an esper entity from an item template."""
    return esper.create_entity(*ITEM_TYPES[key].values())


def deserialize_state(state: list[dict]) -> list[object]:
    """Deserialize state JSON into component instances."""
    return [STATE_ADAPTERS[entry["kind"]].validate_python(entry) for entry in state]


def serialize_state(eid: int, item_key: str) -> list[dict] | None:
    """Serialize only components that differ from the template."""
    template = ITEM_TYPES[item_key]
    return [
        STATE_ADAPTERS[type(comp).__name__].dump_python(comp)
        for cls in STATE_TYPES
        if (comp := esper.try_component(eid, cls)) and comp != template.get(cls)
    ] or None


async def load_world_items(q: AsyncQuerier) -> None:
    """Load world items from the database."""
    map_ids = {eid for eid, _ in esper.get_component(Chips)}
    inventories = []
    for map_id in map_ids:
        inventories.extend([row async for row in q.get_inventories_for_map(map_id=map_id)])
    if not inventories:
        return

    entity_by_inventory: dict[int, int] = {}
    for inv in inventories:
        eid = item_factory(inv.key)
        if inv.state:
            for comp in deserialize_state(inv.state):
                esper.add_component(eid, comp)
        entity_by_inventory[inv.id] = eid

    # Second pass: set up containment and transforms
    for inv in inventories:
        eid = entity_by_inventory[inv.id]
        if inv.container_id:
            esper.add_component(eid, entity_by_inventory[inv.container_id], ContainedBy)
            esper.add_component(eid, Slot(inv.slot))
        elif inv.map_id:
            esper.add_component(eid, Transform(map_id=inv.map_id, x=inv.x, y=inv.y))


async def load_player_inventory(q: AsyncQuerier, owner_id: int, entity_id: int) -> None:
    """Load player inventory from the database."""
    inventories = [row async for row in q.get_inventories_for_owner(owner_id=owner_id)]
    if not inventories:
        return

    entity_by_inventory: dict[int, int] = {}
    for inv in inventories:
        eid = item_factory(inv.key)
        if inv.state:
            for comp in deserialize_state(inv.state):
                esper.add_component(eid, comp)
        entity_by_inventory[inv.id] = eid

    # Second pass: set up containment
    for inv in inventories:
        eid = entity_by_inventory[inv.id]
        container = entity_by_inventory[inv.container_id] if inv.container_id else entity_id
        esper.add_component(eid, container, ContainedBy)
        esper.add_component(eid, Slot(inv.slot))


async def save_owner_inventory(q: AsyncQuerier, owner_id: int, owner_entity: int) -> None:
    """Save player inventory to the database."""
    # Collect all items contained by owner (recursively through containers)
    queue = [owner_entity]
    seen = {owner_entity}
    rows: list[InventoryRow] = []

    while queue:
        container = queue.pop()
        for eid, (item_key, loc, slot) in esper.get_components(ItemKey, ContainedBy, Slot):
            if loc != container or eid in seen or esper.has_component(eid, DoNotSave):
                continue
            seen.add(eid)
            rows.append(InventoryRow(
                id=eid,
                key=item_key.key,
                slot=slot,
                container_id=0 if loc == owner_entity else loc,
                map_id=0,
                x=0,
                y=0,
                state=serialize_state(eid, item_key.key),
                level=esper.try_component(eid, Level) or 0,
                owner_id=owner_id,
            ))
            if esper.has_component(eid, Container):
                queue.append(eid)

    await q.replace_inventories_for_owner(
        ReplaceInventoriesForOwnerParams(
            owner_id=owner_id,
            ids=[r.id for r in rows],
            owner_ids=[r.owner_id for r in rows],
            keys=[r.key for r in rows],
            slots=[r.slot for r in rows],
            container_ids=[r.container_id for r in rows],
            map_ids=[r.map_id for r in rows],
            xs=[r.x for r in rows],
            ys=[r.y for r in rows],
            states=[r.state for r in rows],
            levels=[r.level for r in rows],
        )
    )


async def save_world_inventory(q: AsyncQuerier, map_id: int) -> None:
    """Save world inventory for a map to the database."""
    rows = [
        InventoryRow(
            id=eid,
            key=item_key.key,
            slot="",
            container_id=0,
            map_id=transform.map_id,
            x=transform.x,
            y=transform.y,
            state=serialize_state(eid, item_key.key),
            level=esper.try_component(eid, Level) or 0,
        )
        for eid, (item_key, transform) in esper.get_components(ItemKey, Transform)
        if transform.map_id == map_id and not esper.has_component(eid, DoNotSave)
    ]

    await q.replace_inventories_for_map(
        ReplaceInventoriesForMapParams(
            map_id=map_id,
            ids=[r.id for r in rows],
            keys=[r.key for r in rows],
            slots=[r.slot for r in rows],
            container_ids=[r.container_id for r in rows],
            map_ids=[r.map_id for r in rows],
            xs=[r.x for r in rows],
            ys=[r.y for r in rows],
            states=[r.state for r in rows],
            levels=[r.level for r in rows],
        )
    )
