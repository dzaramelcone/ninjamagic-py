import esper

from ninjamagic import bus
from ninjamagic.component import ChipGrid, Connection, Size, transform


def can_enter(*, grid: ChipGrid, size: Size, y: int, x: int) -> bool:
    h, w = size
    return grid[y * w + x] == 1


def process():
    for sig in bus.iter(bus.MoveCompass):
        loc = transform(sig.source)
        sz = h, w = esper.component_for_entity(loc.map_id, Size)
        grid = esper.component_for_entity(loc.map_id, ChipGrid)

        from_map_id = loc.map_id
        from_y, from_x = loc.y, loc.x

        dir_y, dir_x = sig.dir.to_vector()
        to_y = (from_y + dir_y) % h
        to_x = (from_x + dir_x) % w
        to_map_id = from_map_id

        if not can_enter(grid=grid, size=sz, y=to_y, x=to_x):
            if esper.has_component(sig.source, Connection):
                bus.pulse(bus.Outbound(to=sig.source, text="You can't go there."))
            continue

        # mutate
        loc.y, loc.x = to_y, to_x

        bus.pulse(
            bus.PositionChanged(
                source=sig.source,
                from_map_id=from_map_id,
                from_x=from_x,
                from_y=from_y,
                to_map_id=to_map_id,
                to_x=to_x,
                to_y=to_y,
            )
        )
