import logging
from uuid import uuid4

import esper
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from ninjamagic import bus
from ninjamagic.admin import router as admin_router
from ninjamagic.auth import ChallengeDep, router as auth_router
from ninjamagic.component import OwnerId
from ninjamagic.state import State
from ninjamagic.util import INDEX_HTML, OWNER

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("uvicorn.access")


app = FastAPI(lifespan=State())
app.include_router(router=admin_router)
app.include_router(router=auth_router)
app.add_middleware(SessionMiddleware, secret_key=str(uuid4()))
app.mount("/static", StaticFiles(directory="ninjamagic/static"), name="static")


@app.get("/")
async def index(_: ChallengeDep):
    return HTMLResponse(INDEX_HTML)


@app.websocket("/ws")
async def ws(client: WebSocket) -> None:
    if not (owner_id := client.session.get(OWNER, None)):
        await client.close(code=4401, reason="Unauthorized")
        return

    await client.accept()

    try:
        user_id = esper.create_entity()
        esper.add_component(user_id, owner_id, OwnerId)
        bus.pulse(bus.Connected(source=user_id, client=client))
        while True:
            text = await client.receive_text()
            # TODO: preprocessor for user-defined aliases
            if text[0] == "'":
                text = f"say {text[1:]}"
            bus.pulse(bus.Inbound(source=user_id, text=text))
    except WebSocketDisconnect:
        pass
    finally:
        bus.pulse(bus.Disconnected(source=user_id, client=client))
