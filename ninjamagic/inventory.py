import logging
from dataclasses import fields, is_dataclass

import esper

from ninjamagic import bus
from ninjamagic.component import (
    Anchor,
    Chips,
    ContainedBy,
    Container,
    Food,
    Ingredient,
    InventoryId,
    ItemKey,
    Junk,
    Noun,
    OwnerId,
    ProvidesHeat,
    ProvidesLight,
    Slot,
    Transform,
    Weapon,
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
STATE_REGISTRY: dict[str, type] = {
    "Noun": Noun,
}
STATE_SKIP_FIELDS = {"match_tokens"}

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
}


def item_factory(key: str) -> int:
    """Create an esper entity from an item template.

    Adds all components from ITEM_TYPES[key] to a new entity.
    """
    template = ITEM_TYPES.get(key)
    if template is None:
        raise ValueError(f"Unknown item type: {key}")
    eid = esper.create_entity()
    for comp in template.values():
        esper.add_component(eid, comp)
    return eid


def deserialize_state(state: list[dict]) -> list[object]:
    """Deserialize state JSON into component instances."""
    out: list[object] = []
    for entry in state:
        kind = entry.get("kind")
        if not kind:
            log.warning("State entry missing kind: %s", entry)
            continue
        cls = STATE_REGISTRY.get(kind)
        if cls is None:
            log.warning("Unknown state component kind: %s", kind)
            continue
        if is_dataclass(cls):
            field_names = {field.name for field in fields(cls)}
            data = {k: v for k, v in entry.items() if k in field_names}
            out.append(cls(**data))
        else:
            out.append(cls())
    return out


def serialize_state(eid: int, item_key: str) -> list[dict] | None:
    """Serialize only components that differ from the template.

    Returns None if no components have changed.
    """
    template = ITEM_TYPES.get(item_key)
    if template is None:
        return None

    modified: list[dict] = []
    for cls in STATE_REGISTRY.values():
        comp = esper.try_component(eid, cls)
        if comp is None:
            continue
        template_comp = template.get(cls)
        if comp == template_comp:
            continue
        # Component differs from template - serialize it
        kind = type(comp).__name__
        if is_dataclass(comp):
            data = {
                field.name: getattr(comp, field.name)
                for field in fields(comp)
                if field.name not in STATE_SKIP_FIELDS
            }
            modified.append({"kind": kind, **data})
        else:
            modified.append({"kind": kind})

    return modified if modified else None


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
        try:
            eid = item_factory(inv.key)
        except ValueError as exc:
            log.warning("Failed to create item for inventory %s: %s", inv.id, exc)
            continue

        # Apply state overrides if present
        if inv.state and isinstance(inv.state, list):
            for comp in deserialize_state(inv.state):
                esper.add_component(eid, comp)

        esper.add_component(eid, inv.id, InventoryId)
        entity_by_inventory[inv.id] = eid

    # Second pass: set up containment and transforms
    for inv in inventories:
        eid = entity_by_inventory.get(inv.id)
        if not eid:
            continue
        if inv.container_id is not None:
            container_eid = entity_by_inventory.get(inv.container_id)
            if not container_eid:
                log.warning("Missing container %s for inventory %s", inv.container_id, inv.id)
                continue
            esper.add_component(eid, container_eid, ContainedBy)
            try:
                slot_value = Slot(inv.slot)
            except ValueError:
                slot_value = Slot.ANY
            esper.add_component(eid, slot_value)
            continue
        if inv.map_id is not None and inv.x is not None and inv.y is not None:
            esper.add_component(eid, Transform(map_id=inv.map_id, x=inv.x, y=inv.y))


async def load_player_inventory(q: AsyncQuerier, owner_id: int, entity_id: int) -> None:
    """Load player inventory from the database."""
    inventories = [row async for row in q.get_inventories_for_owner(owner_id=owner_id)]
    if not inventories:
        return

    entity_by_inventory: dict[int, int] = {}
    for inv in inventories:
        try:
            eid = item_factory(inv.key)
        except ValueError as exc:
            log.warning("Failed to create item for inventory %s: %s", inv.id, exc)
            continue

        # Apply state overrides if present
        if inv.state and isinstance(inv.state, list):
            for comp in deserialize_state(inv.state):
                esper.add_component(eid, comp)

        esper.add_component(eid, inv.id, InventoryId)
        entity_by_inventory[inv.id] = eid

    # Second pass: set up containment
    for inv in inventories:
        eid = entity_by_inventory.get(inv.id)
        if not eid:
            continue
        if inv.container_id is not None:
            container_eid = entity_by_inventory.get(inv.container_id)
            if not container_eid:
                log.warning("Missing container %s for inventory %s", inv.container_id, inv.id)
                continue
            esper.add_component(eid, container_eid, ContainedBy)
            try:
                slot_value = Slot(inv.slot)
            except ValueError:
                slot_value = Slot.ANY
            esper.add_component(eid, slot_value)
            continue
        esper.add_component(eid, entity_id, ContainedBy)
        try:
            slot_value = Slot(inv.slot)
        except ValueError:
            slot_value = Slot.ANY
        esper.add_component(eid, slot_value)


async def save_owner_inventory(q: AsyncQuerier, owner_id: int, owner_entity: int) -> None:
    """Save player inventory to the database."""
    owner_component = esper.try_component(owner_entity, OwnerId)
    if owner_component and int(owner_component) != owner_id:
        raise RuntimeError(f"Owner mismatch for entity {owner_entity}")

    # Collect all items contained by owner (recursively through containers)
    queue = [owner_entity]
    seen = {owner_entity}
    item_entities: list[int] = []

    while queue:
        container = queue.pop()
        for eid, (loc, _slot) in esper.get_components(ContainedBy, Slot):
            if loc != container:
                continue
            if eid in seen:
                continue
            if esper.has_component(eid, Junk):
                continue  # Never save junk items
            seen.add(eid)
            item_entities.append(eid)
            if esper.has_component(eid, Container):
                queue.append(eid)

    ids: list[int] = []
    owner_ids: list[int] = []
    keys: list[str] = []
    slots: list[str] = []
    container_ids: list[int] = []
    map_ids: list[int] = []
    xs: list[int] = []
    ys: list[int] = []
    states: list[object | None] = []

    for eid in item_entities:
        inv_id = esper.try_component(eid, InventoryId)
        if not inv_id:
            raise RuntimeError(f"Missing InventoryId for entity {eid}")
        item_key_comp = esper.try_component(eid, ItemKey)
        if not item_key_comp:
            raise RuntimeError(f"Missing ItemKey for entity {eid}")

        loc = esper.try_component(eid, ContainedBy)
        if not loc:
            raise RuntimeError(f"Inventory entity {eid} has no container")

        slot = esper.try_component(eid, Slot) or Slot.ANY
        owner_ids.append(owner_id)
        keys.append(item_key_comp.key)
        ids.append(int(inv_id))
        slots.append(str(slot))
        map_ids.append(-1)
        xs.append(-1)
        ys.append(-1)
        states.append(serialize_state(eid, item_key_comp.key))

        if loc == owner_entity:
            container_ids.append(0)
            continue

        container_inv_id = esper.try_component(loc, InventoryId)
        if not container_inv_id:
            raise RuntimeError(f"Missing InventoryId for container {loc}")
        container_ids.append(int(container_inv_id))

    await q.replace_inventories_for_owner(
        ReplaceInventoriesForOwnerParams(
            owner_id=owner_id,
            ids=ids,
            owner_ids=owner_ids,
            keys=keys,
            slots=slots,
            container_ids=container_ids,
            map_ids=map_ids,
            xs=xs,
            ys=ys,
            states=states,
        )
    )


async def save_world_inventory(q: AsyncQuerier, map_id: int) -> None:
    """Save world inventory for a map to the database."""
    # Collect all world items on this map (items with Transform, no owner)
    ids: list[int] = []
    keys: list[str] = []
    slots: list[str] = []
    container_ids: list[int] = []
    map_ids: list[int] = []
    xs: list[int] = []
    ys: list[int] = []
    states: list[object | None] = []

    entity_by_inventory: dict[int, int] = {}
    for eid, (item_key, transform, inv_id) in esper.get_components(ItemKey, Transform, InventoryId):
        if transform.map_id != map_id:
            continue
        if esper.has_component(eid, Junk):
            continue  # Never save junk items
        entity_by_inventory[int(inv_id)] = eid

    # Build arrays for bulk insert
    for inv_id, eid in entity_by_inventory.items():
        item_key = esper.component_for_entity(eid, ItemKey)
        transform = esper.component_for_entity(eid, Transform)

        ids.append(inv_id)
        keys.append(item_key.key)
        slots.append("")
        container_ids.append(0)
        map_ids.append(transform.map_id)
        xs.append(transform.x)
        ys.append(transform.y)
        states.append(serialize_state(eid, item_key.key))

    await q.replace_inventories_for_map(
        ReplaceInventoriesForMapParams(
            map_id=map_id,
            ids=ids,
            keys=keys,
            slots=slots,
            container_ids=container_ids,
            map_ids=map_ids,
            xs=xs,
            ys=ys,
            states=states,
        )
    )


def process() -> None:
    """Clean up junk item entities at rest check."""
    if bus.is_empty(bus.RestCheck):
        return

    for eid, _ in esper.get_component(Junk):
        esper.delete_entity(eid)
