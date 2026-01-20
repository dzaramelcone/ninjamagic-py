import logging

import esper

from ninjamagic.component import (
    Chips,
    ContainedBy,
    InventoryId,
    ItemTemplateId,
    Slot,
    Transform,
)
from ninjamagic.gen.query import AsyncQuerier
from ninjamagic.item_spec import load_item_spec

log = logging.getLogger(__name__)


def hydrate_item_entity(
    *,
    template_name: str,
    spec: list[dict],
    instance_spec: list[dict] | None = None,
) -> int:
    eid = esper.create_entity()
    _apply_item_spec(eid, spec)
    if instance_spec:
        _apply_item_spec(eid, instance_spec)
    return eid


async def load_world_items(q: AsyncQuerier) -> None:
    map_ids = {eid for eid, _ in esper.get_component(Chips)}
    inventories = []
    for map_id in map_ids:
        inventories.extend(
            [row async for row in q.get_inventories_for_map(map_id=map_id)]
        )
    await _hydrate_inventories(q, inventories, owner_entity=None)


async def load_player_inventory(q: AsyncQuerier, owner_id: int, entity_id: int) -> None:
    inventories = [
        row async for row in q.get_inventories_for_owner(owner_id=owner_id)
    ]
    await _hydrate_inventories(q, inventories, owner_entity=entity_id)


def _apply_item_spec(entity_id: int, spec: list[dict]) -> None:
    for comp in load_item_spec(spec):
        esper.add_component(entity_id, comp)


def _apply_slot(entity_id: int, slot: str) -> None:
    try:
        slot_value = Slot(slot)
    except ValueError:
        slot_value = Slot.ANY
    esper.add_component(entity_id, slot_value)


async def _hydrate_inventories(
    q: AsyncQuerier,
    inventories: list,
    owner_entity: int | None,
) -> None:
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
            _apply_slot(eid, inv.slot)
            continue
        if inv.map_id is not None and inv.x is not None and inv.y is not None:
            esper.add_component(
                eid,
                Transform(map_id=inv.map_id, x=inv.x, y=inv.y),
            )
            continue
        if owner_entity is not None:
            esper.add_component(eid, owner_entity, ContainedBy)
            _apply_slot(eid, inv.slot)
