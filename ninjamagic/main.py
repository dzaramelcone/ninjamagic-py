import logging

import esper
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from ninjamagic import bus, factory
from ninjamagic.auth import CharChallengeDep, router as auth_router
from ninjamagic.component import OwnerId
from ninjamagic.config import settings
from ninjamagic.db import get_repository_factory
from ninjamagic.state import State
from ninjamagic.util import BUILD_HTML, OWNER_SESSION_KEY, VITE_HTML

logging.basicConfig(level=settings.log_level)
log = logging.getLogger(__name__)


app = FastAPI(lifespan=State())
app.include_router(router=auth_router)
app.add_middleware(SessionMiddleware, secret_key=settings.session_secret)
app.mount("/static", StaticFiles(directory="ninjamagic/static/"), name="static")


@app.get("/")
async def index(_: CharChallengeDep):
    if settings.use_vite_proxy:
        return HTMLResponse(VITE_HTML)
    return HTMLResponse(BUILD_HTML)


@app.websocket("/ws")
async def ws_main(ws: WebSocket) -> None:
    if not (owner_id := ws.session.get(OWNER_SESSION_KEY, None)):
        await ws.close(code=4401, reason="Unauthorized")
        return
    async with get_repository_factory() as q:
        char = await q.get_character(owner_id=owner_id)
        if not char:
            await ws.close(code=4401, reason="No character")

    log.info("loaded %s", char.model_dump_json())

    await ws.accept()

    try:
        host, port = ws.client.host, ws.client.port
        entity_id = esper.create_entity()
        esper.add_component(entity_id, owner_id, OwnerId)
        log.info("%s:%s - [%s] WS/LOGIN", host, port, owner_id)

        bus.pulse(bus.Connected(source=entity_id, client=ws, char=char))
        while True:
            text = await ws.receive_text()
            log.info("%s:%s - [%s] WS/RECV: %s", host, port, owner_id, text)
            # TODO: preprocessor for input cleanup and user-defined aliases
            if text[0] == "'":
                text = f"say {text[1:]}"
            bus.pulse(bus.Inbound(source=entity_id, text=text))
    except WebSocketDisconnect:
        pass
    finally:
        log.info("%s:%s - WS/LOGOUT [%s]", host, port, owner_id)
        bus.pulse(bus.Disconnected(source=entity_id, client=ws))
        async with get_repository_factory() as q:
            await q.update_character(factory.dump(entity_id))
