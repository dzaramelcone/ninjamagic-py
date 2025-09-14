import logging
from uuid import uuid4
import esper
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from starlette.middleware.sessions import SessionMiddleware
from ninjamagic import bus
from ninjamagic.util import ACCOUNT, Subject
from ninjamagic.state import State
from ninjamagic.auth import router as auth_router
from fastapi.staticfiles import StaticFiles
app = FastAPI(lifespan=State())

app.include_router(router=auth_router)
app.add_middleware(SessionMiddleware, secret_key=str(uuid4()))
app.mount("/static", StaticFiles(directory="ninjamagic/static"), name="static")

@app.get("/")
async def index(request: Request):
    if not request.session.get("user"):
        return RedirectResponse(url="/auth", status_code=303)
    return HTMLResponse("""
<!doctype html>
<meta charset="utf-8"/>
<title>ECS Chat</title>
<style>
  body { font: 14px/1.4 system-ui, -apple-system, Segoe UI, Roboto, sans-serif; margin: 2rem; }
  #log { border: 1px solid #ccc; height: 300px; padding: .5rem; overflow: auto; white-space: pre-wrap; }
  #bar { margin-top: .5rem; display: flex; gap: .5rem; }
  input, button { font: inherit; padding: .4rem .6rem; }
  #name { width: 10rem; }
  #msg { flex: 1; }
</style>
<div>
  <h1>ECS Chat</h1>
  <div id="log"></div>
  <div id="bar">
    <input id="name" placeholder="name" />
    <input id="msg" placeholder="message" />
    <button id="send">send</button>ç
  </div>
</div>
<script>
let ws;
const logEl = document.querySelector('#log');
const nameEl = document.querySelector('#name');
const msgEl = document.querySelector('#msg');
const sendBtn = document.querySelector('#send');

function append(line) {
  logEl.textContent += line + "\\n";
  logEl.scrollTop = logEl.scrollHeight;
}

function connect() {
  const url = new URL("/ws", location.href);
  url.protocol = url.protocol.replace("http", "ws");
  ws = new WebSocket(url.toString());
  ws.onopen = () => append("• connected");
  ws.onclose = () => append("• disconnected");
  ws.onmessage = (ev) => {
    try {
      const data = JSON.parse(ev.data);
      if (data.type === "chat") append(data.line);
      else append(ev.data);
    } catch {
      append(ev.data);
    }
  };
}

sendBtn.onclick = () => {
  const name = nameEl.value.trim() || "anon";
  const text = msgEl.value.trim();
  if (!text) return;
  ws?.send(text);
  msgEl.value = "";
  msgEl.focus();
};

msgEl.addEventListener("keydown", (e) => {
  if (e.key === "Enter") sendBtn.click();
});

connect();
</script>
""")

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("uvicorn.access")

@app.websocket("/ws")
async def ws(client: WebSocket) -> None:
    if not (account := client.session.get(ACCOUNT, None)):
        await client.close(code=4401, reason="Unauthorized")
        return

    await client.accept()
    try:
        user_id = esper.create_entity()
        esper.add_component(user_id, account.get("subject"), Subject)
        bus.fire(bus.Connected(source=user_id, client=client))
        while True:
            text = await client.receive_text()
            bus.fire(bus.Inbound(source=user_id, text=text))
    except WebSocketDisconnect:
        pass
    finally:
        bus.fire(bus.Disconnected(source=user_id, client=client))
