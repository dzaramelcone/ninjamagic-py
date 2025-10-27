import logging

import esper
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from ninjamagic import bus
from ninjamagic.auth import ChallengeDep, router as auth_router
from ninjamagic.component import OwnerId
from ninjamagic.config import settings
from ninjamagic.state import State
from ninjamagic.util import BUILD_HTML, OWNER_SESSION_KEY, VITE_HTML
from ninjamagic.world.router import router as world_router

logging.basicConfig(level=settings.log_level)
log = logging.getLogger(__name__)


app = FastAPI(lifespan=State())
app.include_router(router=auth_router)
app.include_router(router=world_router)
app.add_middleware(SessionMiddleware, secret_key=settings.session_secret)
app.mount("/static", StaticFiles(directory="ninjamagic/static/"), name="static")


@app.get("/")
async def index(_: ChallengeDep):
    if settings.use_vite_proxy:
        return HTMLResponse(VITE_HTML)
    return HTMLResponse(BUILD_HTML)


@app.websocket("/ws")
async def ws_main(ws: WebSocket) -> None:
    if not (owner_id := ws.session.get(OWNER_SESSION_KEY, None)):
        await ws.close(code=4401, reason="Unauthorized")
        return

    await ws.accept()

    try:
        host, port = ws.client.host, ws.client.port
        user_id = esper.create_entity()
        esper.add_component(user_id, owner_id, OwnerId)
        log.info("%s:%s - [%s] WS/LOGIN", host, port, owner_id)
        bus.pulse(bus.Connected(source=user_id, client=ws))
        while True:
            text = await ws.receive_text()
            log.info("%s:%s - [%s] WS/RECV: %s", host, port, owner_id, text)
            # TODO: preprocessor for input cleanup and user-defined aliases
            if text[0] == "'":
                text = f"say {text[1:]}"
            bus.pulse(bus.Inbound(source=user_id, text=text))
    except WebSocketDisconnect:
        pass
    finally:
        log.info("%s:%s - WS/LOGOUT [%s]", host, port, owner_id)
        bus.pulse(bus.Disconnected(source=user_id, client=ws))
