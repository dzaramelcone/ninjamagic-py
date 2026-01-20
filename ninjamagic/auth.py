import logging
import re
from typing import Annotated, Literal

from authlib.integrations.starlette_client import OAuth
from fastapi import APIRouter, Depends, Form, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.exc import IntegrityError

from ninjamagic.component import Noun, Transform
from ninjamagic.config import settings
from ninjamagic.db import Repository
from ninjamagic.gen.models import OauthProvider, Pronoun
from ninjamagic.gen.query import GetCharacterBriefRow, UpdateCharacterParams
from ninjamagic.state import ClientDep
from ninjamagic.util import CHARGEN_HTML, LOGIN_HTML, OWNER_SESSION_KEY

oauth = OAuth()
router = APIRouter(prefix="/auth")
log = logging.getLogger(__name__)

google = oauth.register(
    name=OauthProvider.GOOGLE,
    client_id=settings.google.client,
    client_secret=settings.google.secret,
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs={"scope": "openid email"},
)

discord = oauth.register(
    name=OauthProvider.DISCORD,
    client_id=settings.discord.client,
    client_secret=settings.discord.secret,
    access_token_url="https://discord.com/api/oauth2/token",
    authorize_url="https://discord.com/api/oauth2/authorize",
    api_base_url="https://discord.com/api",
    client_kwargs={"scope": "identify email"},
)


async def get_owner_id(request: Request) -> str:
    return request.session.get(OWNER_SESSION_KEY, "")


OwnerDep = Annotated[str, Depends(get_owner_id)]


async def owner_challenge(owner: OwnerDep) -> str:
    if not owner:
        raise HTTPException(status_code=303, headers={"location": "/auth/"})
    return owner


OwnerChallengeDep = Annotated[str, Depends(owner_challenge)]


async def get_character(
    owner: OwnerChallengeDep, q: Repository
) -> GetCharacterBriefRow | None:
    return await q.get_character_brief(owner_id=owner)


CharacterDep = Annotated[GetCharacterBriefRow | None, Depends(get_character)]


async def character_challenge(
    owner: OwnerDep, char: CharacterDep
) -> GetCharacterBriefRow:
    log.info("Character challenge for %s", owner)
    log.info("Got %s", char)
    if not char:
        raise HTTPException(status_code=303, headers={"location": "/auth/chargen/"})
    return char


CharChallengeDep = Annotated[GetCharacterBriefRow, Depends(character_challenge)]


@router.get("/chargen")
async def get_chargen(_: OwnerChallengeDep, char: CharacterDep):
    if char:
        return RedirectResponse(url="/", status_code=303)
    return HTMLResponse(CHARGEN_HTML)


@router.post("/chargen")
async def post_chargen(
    owner_id: OwnerChallengeDep,
    char: CharacterDep,
    q: Repository,
    char_name: Annotated[str, Form()],
    pronoun: Annotated[Literal["she", "he", "it", "they"], Form()],
):
    if char:
        return RedirectResponse(url="/", status_code=303)

    name = char_name.strip().capitalize()

    name_pattern = re.compile(r"^[a-zA-Z]{3,20}$")
    if not name_pattern.match(name):
        err = f"The name '{name}' is invalid."
        return RedirectResponse(url=f"chargen/?error={err}", status_code=303)

    try:
        new = await q.create_character(owner_id=owner_id, name=name, pronoun=pronoun)
    except IntegrityError:
        err = f"The name '{name}' is taken."
        return RedirectResponse(url=f"chargen/?error={err}", status_code=303)

    log.info(
        "New character created for owner %s: %s %s",
        owner_id,
        new.name,
        pronoun,
    )

    return RedirectResponse(url="/", status_code=303)


@router.get("/", include_in_schema=False)
async def login(owner: OwnerDep):
    if owner:
        return RedirectResponse(url="/", status_code=303)
    return HTMLResponse(LOGIN_HTML)


@router.get("/google/login")
async def login_via_google(req: Request, owner: OwnerDep):
    if owner:
        return RedirectResponse(url="/", status_code=303)

    return await google.authorize_redirect(
        req,
        req.url_for("auth_via_google"),
        prompt="none",
    )


@router.get("/google")
async def auth_via_google(req: Request, q: Repository):
    if req.query_params.get("error"):
        return await google.authorize_redirect(req, req.url_for("auth_via_google"))

    token = await google.authorize_access_token(req)
    usr = token["userinfo"]
    owner_id = await q.upsert_identity(
        provider=OauthProvider.GOOGLE,
        subject=usr.get("sub"),
        email=usr.get("email"),
    )
    req.session[OWNER_SESSION_KEY] = owner_id
    return RedirectResponse(url="/", status_code=303)


@router.get("/discord/login")
async def login_via_discord(req: Request, owner: OwnerDep):
    if owner:
        return RedirectResponse(url="/", status_code=303)
    return await discord.authorize_redirect(
        req,
        req.url_for("auth_via_discord"),
        prompt="none",
    )


@router.get("/discord")
async def auth_via_discord(req: Request, q: Repository, client: ClientDep):
    if req.query_params.get("error"):
        return await discord.authorize_redirect(
            req,
            req.url_for("auth_via_discord"),
        )

    token = await discord.authorize_access_token(req)
    token = token["access_token"]
    resp = await client.get(
        "https://discord.com/api/users/@me",
        headers={"Authorization": f"Bearer {token}"},
    )
    usr = resp.json()

    owner_id = await q.upsert_identity(
        provider=OauthProvider.DISCORD,
        subject=usr.get("id"),
        email=usr.get("email"),
    )
    req.session[OWNER_SESSION_KEY] = owner_id
    return RedirectResponse(url="/", status_code=303)


if settings.allow_local_auth:
    from tests.conftest import FakeUserSetup

    log.warning("Using local auth. Do not use this in production.")

    @router.get("/local")
    async def auth_via_local_get(
        req: Request, q: Repository, name: Annotated[str, Query()] = ""
    ):
        from uuid import uuid4

        return await auth_via_local(
            req=req,
            q=q,
            body=FakeUserSetup(
                subj=str(uuid4()),
                email=str(uuid4()),
                noun=Noun(value=name or str(uuid4())),
                transform=Transform(map_id=2, x=6, y=6),
            ),
        )

    @router.post("/local")
    async def auth_via_local(
        req: Request,
        q: Repository,
        body: FakeUserSetup,
    ):
        owner_id = await q.upsert_identity(
            provider=OauthProvider.DISCORD,
            subject=body.subj,
            email=body.email,
        )

        char = await q.get_character_brief(owner_id=owner_id)
        if not char:
            char = await q.create_character(
                owner_id=owner_id,
                name=body.noun.value,
                pronoun=Pronoun(body.noun.pronoun.they),
            )
        g, h, s, v = body.glyph
        await q.update_character(
            arg=UpdateCharacterParams(
                id=char.id,
                glyph=g,
                glyph_h=h,
                glyph_s=s,
                glyph_v=v,
                pronoun=Pronoun(body.noun.pronoun.they),
                map_id=body.transform.map_id,
                x=body.transform.x,
                y=body.transform.y,
                health=body.health.cur,
                stress=body.health.stress,
                aggravated_stress=body.health.aggravated_stress,
                stance=body.stance.cur,
                condition=body.health.condition,
                grace=body.stats.grace,
                grit=body.stats.grit,
                wit=body.stats.wit,
            )
        )
        await q.upsert_skills(
            char_id=char.id,
            names=[skill.name for skill in body.skills],
            ranks=[skill.rank for skill in body.skills],
            tnls=[skill.tnl for skill in body.skills],
        )
        req.session[OWNER_SESSION_KEY] = owner_id

        return RedirectResponse(url="/", status_code=303)
