import asyncio
import contextlib
import logging
from weakref import WeakValueDictionary

import esper
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from ninjamagic import bus, db, factory, inventory
from ninjamagic.auth import CharChallengeDep, router as auth_router
from ninjamagic.component import Chips, EntityId, OwnerId, Prompt
from ninjamagic.config import settings
from ninjamagic.gen.query import UpsertSkillsParams
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


owner_locks: WeakValueDictionary[OwnerId, asyncio.Lock] = WeakValueDictionary()
active: dict[OwnerId, WebSocket] = {}
active_save_loops: dict[OwnerId, int] = {}


@app.websocket("/ws")
async def ws_main(ws: WebSocket) -> None:
    if not (owner_id := ws.session.get(OWNER_SESSION_KEY, None)):
        await ws.close(code=4401, reason="Unauthorized")
        return
    lock = owner_locks.setdefault(owner_id, asyncio.Lock())
    if old_ws := active.get(owner_id):
        with contextlib.suppress(WebSocketDisconnect, RuntimeError):
            log.info(f"Dual login for {owner_id}, kicking old connection.")
            await old_ws.close(code=4000, reason="Logged in from another location.")
    try:
        await asyncio.wait_for(lock.acquire(), timeout=5.0)
    except TimeoutError:
        log.error(f"Login failed for {owner_id}: Previous session execution is stuck.")
        await ws.close(code=4000, reason="Session handover timed out. Please retry.")
        return

    try:
        entity_id = esper.create_entity()
        esper.add_component(entity_id, owner_id, OwnerId)
        async with db.get_repository_factory() as q:
            char = await q.get_character(owner_id=owner_id)
            if not char:
                log.info(f"Login failed for {owner_id}, no character.")
                await ws.close(code=4401, reason="No character")
                esper.delete_entity(entity_id)
                return
            skills = [row async for row in q.get_skills_for_character(char_id=char.id)]
            factory.load(entity_id, char, skills)
            await inventory.load_player_inventory(
                q,
                owner_id=char.id,
                entity_id=entity_id,
            )
        await ws.accept()

        active[owner_id] = ws

        save_gen = active_save_loops.get(owner_id, 0) + 1
        active_save_loops[owner_id] = save_gen

        host, port = ws.client.host, ws.client.port
        log.info(
            "%s:%s WS/LOGIN - [%s:%s->%s]: %s",
            host,
            port,
            owner_id,
            entity_id,
            char.id,
            char.name,
        )

        bus.pulse(bus.Connected(source=entity_id, client=ws, char=char, skills=skills))
        asyncio.create_task(save_loop(owner_id, entity_id, save_gen))

        try:
            while True:
                text = await ws.receive_text()
                log.info(
                    "%s:%s WS/RECV - [%s:%s->%s]: %s: %s",
                    host,
                    port,
                    owner_id,
                    entity_id,
                    char.id,
                    char.name,
                    text,
                )

                if prompt := esper.try_component(entity_id, Prompt):
                    bus.pulse(
                        bus.InboundPrompt(source=entity_id, text=text, prompt=prompt)
                    )
                    continue

                bus.pulse(bus.Inbound(source=entity_id, text=text))
        except WebSocketDisconnect:
            pass
        except Exception as e:
            log.error(f"Unexpected WS error for {owner_id}: {e}", exc_info=True)
        finally:
            log.info(
                "%s:%s WS/LOGOUT - [%s:%s->%s]: %s",
                host,
                port,
                owner_id,
                entity_id,
                char.id,
                char.name,
            )
            bus.pulse(bus.Disconnected(source=entity_id, client=ws))
            if active_save_loops.get(owner_id) == save_gen:
                active_save_loops.pop(owner_id)
            if active.get(owner_id) is ws:
                active.pop(owner_id)
            await save(entity_id)

    finally:
        lock.release()


async def save(entity_id: EntityId):
    save_dump, skills_dump = factory.dump(entity_id)
    log.info("saving entity %s", save_dump.model_dump_json(indent=1))
    async with db.get_repository_factory() as q:
        await inventory.save_player_inventory(
            q,
            owner_id=save_dump.id,
            owner_entity=entity_id,
        )
        await q.update_character(save_dump)
        await q.upsert_skills(UpsertSkillsParams(
            char_id=save_dump.id,
            names=[skill.name for skill in skills_dump],
            ranks=[skill.rank for skill in skills_dump],
            tnls=[skill.tnl for skill in skills_dump],
            pendings=[skill.pending for skill in skills_dump],
        ))
        log.info("%s saved.", entity_id)


async def save_loop(owner_id: OwnerId, entity_id: EntityId, generation: int):
    await asyncio.sleep(settings.save_character_rate)
    while (
        esper.entity_exists(entity_id)
        and active_save_loops.get(owner_id, 0) == generation
    ):
        await save(entity_id)
        await asyncio.sleep(settings.save_character_rate)


async def world_save_loop():
    while True:
        await asyncio.sleep(settings.save_character_rate)
        map_ids = [eid for eid, _ in esper.get_component(Chips)]
        if not map_ids:
            continue
        async with db.get_repository_factory() as q:
            for map_id in map_ids:
                await inventory.save_map_inventory(q, map_id)
