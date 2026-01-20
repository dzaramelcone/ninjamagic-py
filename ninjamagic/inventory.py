import logging
from dataclasses import fields, is_dataclass

import esper

from ninjamagic import bus
from ninjamagic.component import (
    Chips,
    ContainedBy,
    Container,
    InventoryId,
    ItemTemplateId,
    Junk,
    Noun,
    OwnerId,
    Slot,
    Transform,
    Weapon,
)
from ninjamagic.db import get_repository_factory
from ninjamagic.gen.query import (
    AsyncQuerier,
    InsertInventoriesForOwnerParams,
)

log = logging.getLogger(__name__)

# Item spec serialization lives here so inventory persistence stays in one module.
ITEM_SPEC_REGISTRY = {
    "Noun": Noun,
    "Weapon": Weapon,
}
ITEM_SPEC_SKIP_FIELDS = {"match_tokens"}


def dump_item_spec(components: list[object]) -> list[dict]:
    spec: list[dict] = []
    for comp in components:
        kind = type(comp).__name__
        if is_dataclass(comp):
            data = {
                field.name: getattr(comp, field.name)
                for field in fields(comp)
                if field.name not in ITEM_SPEC_SKIP_FIELDS
            }
            spec.append({"kind": kind, **data})
        else:
            spec.append({"kind": kind})
    return spec


def load_item_spec(spec: list[dict]) -> list[object]:
    out: list[object] = []
    for entry in spec:
        kind = entry.get("kind")
        if not kind:
            raise ValueError("item spec missing kind")
        cls = ITEM_SPEC_REGISTRY.get(kind)
        if cls is None:
            raise ValueError(f"unknown item component: {kind}")
        if is_dataclass(cls):
            field_names = {field.name for field in fields(cls)}
            data = {key: value for key, value in entry.items() if key in field_names}
            out.append(cls(**data))
        else:
            out.append(cls())
    return out


# Hydration keeps a direct spec->components flow so that the DB format stays visible.
# This makes the file big, but it makes the data flow easy to audit.

def hydrate_item_entity(
    *,
    template_name: str,
    spec: list[dict],
    instance_spec: list[dict] | None = None,
) -> int:
    eid = esper.create_entity()
    for comp in load_item_spec(spec):
        esper.add_component(eid, comp)
    if instance_spec:
        for comp in load_item_spec(instance_spec):
            esper.add_component(eid, comp)
    return eid


async def load_world_items(q: AsyncQuerier) -> None:
    # World item hydration is explicit and verbose so the DB->ECS mapping is easy to trace.
    map_ids = {eid for eid, _ in esper.get_component(Chips)}
    inventories = []
    for map_id in map_ids:
        inventories.extend(
            [row async for row in q.get_inventories_for_map(map_id=map_id)]
        )
    if not inventories:
        return

    item_ids = sorted({inv.item_id for inv in inventories})
    items = {item.id: item async for item in q.get_items_by_ids(dollar_1=item_ids)}

    entity_by_inventory: dict[int, int] = {}
    for inv in inventories:
        item = items.get(inv.item_id)
        if not item:
            log.warning("Missing item template %s for inventory %s", inv.item_id, inv.id)
            continue
        try:
            spec = item.spec if isinstance(item.spec, list) else []
            instance_spec = inv.instance_spec if isinstance(inv.instance_spec, list) else None
            eid = hydrate_item_entity(
                template_name=item.name,
                spec=spec,
                instance_spec=instance_spec,
            )
        except ValueError as exc:
            log.warning("Invalid item spec for inventory %s: %s", inv.id, exc)
            continue
        entity_by_inventory[inv.id] = eid
        esper.add_component(eid, item.id, ItemTemplateId)
        esper.add_component(eid, inv.id, InventoryId)

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
            esper.add_component(
                eid,
                Transform(map_id=inv.map_id, x=inv.x, y=inv.y),
            )


async def load_player_inventory(q: AsyncQuerier, owner_id: int, entity_id: int) -> None:
    # Player inventory hydration mirrors world hydration but roots containment to the player.
    inventories = [
        row async for row in q.get_inventories_for_owner(owner_id=owner_id)
    ]
    if not inventories:
        return

    item_ids = sorted({inv.item_id for inv in inventories})
    items = {item.id: item async for item in q.get_items_by_ids(dollar_1=item_ids)}

    entity_by_inventory: dict[int, int] = {}
    for inv in inventories:
        item = items.get(inv.item_id)
        if not item:
            log.warning("Missing item template %s for inventory %s", inv.item_id, inv.id)
            continue
        try:
            spec = item.spec if isinstance(item.spec, list) else []
            instance_spec = inv.instance_spec if isinstance(inv.instance_spec, list) else None
            eid = hydrate_item_entity(
                template_name=item.name,
                spec=spec,
                instance_spec=instance_spec,
            )
        except ValueError as exc:
            log.warning("Invalid item spec for inventory %s: %s", inv.id, exc)
            continue
        entity_by_inventory[inv.id] = eid
        esper.add_component(eid, item.id, ItemTemplateId)
        esper.add_component(eid, inv.id, InventoryId)

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


# Save is intentionally long and linear: build the full owner inventory, delete rows,
# and bulk insert. This avoids hidden state and makes the DB transaction explicit.
async def save_owner_inventory(q: AsyncQuerier, owner_id: int, owner_entity: int) -> None:
    owner_component = esper.try_component(owner_entity, OwnerId)
    if owner_component and int(owner_component) != owner_id:
        raise RuntimeError(f"Owner mismatch for entity {owner_entity}")

    queue = [owner_entity]
    seen = {owner_entity}
    item_entities: list[int] = []

    while queue:
        container = queue.pop()
        for eid, (loc, slot) in esper.get_components(ContainedBy, Slot):
            if loc != container:
                continue
            if eid in seen:
                continue
            seen.add(eid)
            item_entities.append(eid)
            if esper.has_component(eid, Container):
                queue.append(eid)

    ids: list[int] = []
    owner_ids: list[int] = []
    item_ids: list[int] = []
    slots: list[str] = []
    container_ids: list[int] = []
    map_ids: list[int] = []
    xs: list[int] = []
    ys: list[int] = []
    instance_specs: list[object | None] = []

    for eid in item_entities:
        inv_id = esper.try_component(eid, InventoryId)
        if not inv_id:
            raise RuntimeError(f"Missing InventoryId for entity {eid}")
        template_id = esper.try_component(eid, ItemTemplateId)
        if not template_id:
            raise RuntimeError(f"Missing ItemTemplateId for entity {eid}")

        loc = esper.try_component(eid, ContainedBy)
        if not loc:
            raise RuntimeError(f"Inventory entity {eid} has no container")

        slot = esper.try_component(eid, Slot) or Slot.ANY
        owner_ids.append(owner_id)
        item_ids.append(int(template_id))
        ids.append(int(inv_id))
        slots.append(str(slot))
        map_ids.append(-1)
        xs.append(-1)
        ys.append(-1)
        instance_specs.append(None)

        if loc == owner_entity:
            container_ids.append(0)
            continue

        container_inv_id = esper.try_component(loc, InventoryId)
        if not container_inv_id:
            raise RuntimeError(f"Missing InventoryId for container {loc}")
        container_ids.append(int(container_inv_id))

    await q.delete_inventories_for_owner(owner_id=owner_id)
    if not ids:
        return

    await q.insert_inventories_for_owner(
        InsertInventoriesForOwnerParams(
            ids=ids,
            owner_ids=owner_ids,
            item_ids=item_ids,
            slots=slots,
            container_ids=container_ids,
            map_ids=map_ids,
            xs=xs,
            ys=ys,
            instance_specs=instance_specs,
        )
    )


async def process() -> None:
    # RestCheck cleanup deletes junk entities and their inventory rows in the same tick.
    if bus.is_empty(bus.RestCheck):
        return

    inventory_ids: list[int] = []
    for eid, _ in esper.get_component(Junk):
        if inv_id := esper.try_component(eid, InventoryId):
            inventory_ids.append(int(inv_id))
        esper.delete_entity(eid)

    if not inventory_ids:
        return

    async with get_repository_factory() as q:
        for inventory_id in inventory_ids:
            await q.delete_inventory_by_id(id=inventory_id)
