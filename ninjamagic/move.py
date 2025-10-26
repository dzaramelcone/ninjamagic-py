import esper

from ninjamagic import bus
from ninjamagic.component import Connection, transform
from ninjamagic.util import Size
from ninjamagic.world.state import ChipGrid


def process():
    for sig in bus.iter(bus.MoveCompass):
        loc = transform(sig.source)

        maybe_sz_grid = esper.try_components(loc.map_id, Size, ChipGrid)
        if not maybe_sz_grid:
            raise KeyError(f"Entity {loc.map_id} missing Size or Grid, is it a map?")

        sz, grid = maybe_sz_grid
        from_map_id = loc.map_id
        from_y, from_x = loc.y, loc.x

        dir_y, dir_x = sig.dir.to_vector()
        to_y = (from_y + dir_y) % sz.height
        to_x = (from_x + dir_x) % sz.width
        to_map_id = from_map_id

        if grid[to_y, to_x] != 1:
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
