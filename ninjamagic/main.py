import logging
from uuid import uuid4
import esper
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from starlette.middleware.sessions import SessionMiddleware
from ninjamagic import bus
from ninjamagic.util import ACCOUNT, AccountId
from ninjamagic.state import State
from ninjamagic.auth import router as auth_router
from fastapi.staticfiles import StaticFiles


logging.basicConfig(level=logging.INFO)
log = logging.getLogger("uvicorn.access")

index_html = open("ninjamagic/static/index.html", "r").read()

app = FastAPI(lifespan=State())

app.include_router(router=auth_router)
app.add_middleware(SessionMiddleware, secret_key=str(uuid4()))
app.mount("/static", StaticFiles(directory="ninjamagic/static"), name="static")


@app.get("/")
async def index(request: Request):
    if not request.session.get("user"):
        return RedirectResponse(url="/auth/", status_code=303)
    return HTMLResponse(index_html)


@app.websocket("/ws")
async def ws(client: WebSocket) -> None:
    if not (owner_id := client.session.get(ACCOUNT, None)):
        await client.close(code=4401, reason="Unauthorized")
        return

    await client.accept()
    try:
        user_id = esper.create_entity()
        esper.add_component(user_id, owner_id, AccountId)
        bus.fire(bus.Connected(source=user_id, client=client))
        while True:
            text = await client.receive_text()
            bus.fire(bus.Inbound(source=user_id, text=text))
    except WebSocketDisconnect:
        pass
    finally:
        bus.fire(bus.Disconnected(source=user_id, client=client))
