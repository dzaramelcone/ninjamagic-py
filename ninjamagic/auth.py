import httpx

from authlib.integrations.starlette_client import OAuth
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from ninjamagic.config import settings
from ninjamagic.gen.models import OauthProvider
from ninjamagic.db import Repository
from ninjamagic.util import OWNER, LOGIN_HTML

oauth = OAuth()
router = APIRouter(prefix="/auth")

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


@router.get("/", include_in_schema=False)
async def login(req: Request):
    if req.session.get(OWNER, None):
        return RedirectResponse(url="/", status_code=303)
    return HTMLResponse(LOGIN_HTML)


@router.get("/google/login")
async def login_via_google(req: Request):
    if req.session.get(OWNER, None):
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
    account = await q.upsert_identity(
        provider=OauthProvider.GOOGLE,
        subject=usr.get("sub"),
        email=usr.get("email"),
    )
    req.session[OWNER] = account
    return RedirectResponse(url="/", status_code=303)


@router.get("/discord/login")
async def login_via_discord(req: Request):
    if req.session.get(OWNER, None):
        return RedirectResponse(url="/", status_code=303)
    return await discord.authorize_redirect(
        req,
        req.url_for("auth_via_discord"),
        prompt="none",
    )


@router.get("/discord")
async def auth_via_discord(req: Request, q: Repository):
    if req.query_params.get("error"):
        return await discord.authorize_redirect(
            req,
            req.url_for("auth_via_discord"),
        )

    token = await discord.authorize_access_token(req)
    token = token["access_token"]
    client = httpx.AsyncClient()
    resp = await client.get(
        "https://discord.com/api/users/@me",
        headers={"Authorization": f"Bearer {token}"},
    )
    usr = resp.json()

    account = await q.upsert_identity(
        provider=OauthProvider.DISCORD,
        subject=usr.get("id"),
        email=usr.get("email"),
    )
    req.session[OWNER] = account
    return RedirectResponse(url="/", status_code=303)
