import logging
import esper
from ninjamagic import bus
from ninjamagic.util import Connection


log = logging.getLogger(__name__)

def process():
    for c in bus.connected:
        log.info("%s:%s connected.", c.source, c.client)
        esper.add_component(entity=c.source, component_instance=c.client, type_alias=Connection)

    for d in bus.disconnected:
        log.info(f"%s:%s disconnected.", d.client,d.source)
        esper.remove_component(entity=d.source, component_type=Connection)
