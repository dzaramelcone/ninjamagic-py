import esper

from ninjamagic import bus


def process():
    for sig in bus.iter(bus.Cleanup):
        for c in sig.removed_components:
            if esper.has_component(sig.source, c):
                esper.remove_component(sig.source, c)
