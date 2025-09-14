import httpx

from authlib.integrations.starlette_client import OAuth
from enum import StrEnum
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import BaseModel
from starlette.requests import Request

from ninjamagic.config import settings
from ninjamagic.db import Repository
from ninjamagic.util import ACCOUNT

oauth = OAuth()
router = APIRouter(prefix="/auth")
class Provider(StrEnum):
    GOOGLE = "google"
    DISCORD = "discord"

class Account(BaseModel):
    provider: Provider
    subject: str
    email: str

google = oauth.register(
    name=Provider.GOOGLE,
    client_id=settings.google.client,
    client_secret=settings.google.secret,
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs={"scope": "openid email"},
)

discord = oauth.register(
    name=Provider.DISCORD,
    client_id=settings.discord.client,
    client_secret=settings.discord.secret,
    access_token_url='https://discord.com/api/oauth2/token',
    authorize_url='https://discord.com/api/oauth2/authorize',
    api_base_url='https://discord.com/api',
    client_kwargs={'scope': 'identify email'}
)



@router.get("/", include_in_schema=False)
async def login(req: Request):
    if req.session.get(ACCOUNT, None):
        return RedirectResponse(url="/", status_code=303)

    return HTMLResponse(
        """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width,initial-scale=1" />
  <title>Sign in</title>
  <style>
    :root { color-scheme: light dark; --mono:#6b7280; }
    * { box-sizing: border-box; }
    body { margin:0; font-family: system-ui, -apple-system, Segoe UI, Roboto, sans-serif; }
    .wrap { min-height: 100svh; display:grid; place-items:center; padding:20px; }
    .card {
      width:100%; max-width:420px;
      border:1px solid rgba(0,0,0,.12);
      border-radius:16px; padding:16px 18px 20px;
      box-shadow: 0 8px 24px rgba(0,0,0,.08);
      display:grid; gap:12px; background:#fff;
    }
    .hdr { display:flex; align-items:center; gap:8px; }
    .door { width:16px; height:16px; color:var(--mono); flex:0 0 auto; }

    .grid {
      display:grid; grid-template-columns: repeat(2, 1fr);
      gap:10px; width:100%; max-width:260px; margin:4px auto 0;
    }
    .btn {
      display:grid; place-items:center;
      width:100%; aspect-ratio: 2.1 / 1;
      border-radius:10px;
      background:#f3f4f6; border:1px solid #d1d5db;
      text-decoration:none; outline:none; overflow:hidden;
      transition:transform .06s ease, filter .12s ease, box-shadow .12s ease;
    }
    .btn:hover { filter:brightness(.98); box-shadow: 0 2px 8px rgba(0,0,0,.06); }
    .btn:active { transform: translateY(1px); }
    .btn:focus-visible { box-shadow: 0 0 0 3px rgba(24,119,242,.25); }

    .ico {
      width:24px; height:24px; display:block;
      background-color: var(--mono);
      -webkit-mask-repeat:no-repeat; -webkit-mask-position:center; -webkit-mask-size:contain;
      mask-repeat:no-repeat; mask-position:center; mask-size:contain;
    }
    .ico.google  { -webkit-mask-image:url("/static/icons/google.svg");  mask-image:url("/static/icons/google.svg"); }
    .ico.discord { -webkit-mask-image:url("/static/icons/discord.svg"); mask-image:url("/static/icons/discord.svg"); }

    .stripes {
      display:grid; grid-template-columns: 1fr 1fr;
      gap:10px; width:100%; max-width:260px;
      margin:10px auto 8px; /* slight space beneath */
    }
    .stripe { height:3px; background:#e5e7eb; border-radius:999px; }

    .muted { color:#888; text-align:center; }

    @media (prefers-color-scheme: dark) {
      body { background:#0b0b0b; }
      .card { border-color: rgba(255,255,255,.12); box-shadow:none; background:#111; }
      .btn  { background:#151515; border-color:#2a2a2a; }
      :root { --mono:#9ca3af; }
      .stripe { background:#2a2a2a; }
      .muted { color:#aaa; }
    }
  </style>
</head>
<body>
  <div class="wrap">
    <div class="card">
      <div class="hdr" aria-hidden="true">
        <svg class="door" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">
          <rect x="3" y="3" width="12" height="18" rx="1.6"></rect>
          <path d="M9 12h12"></path>
          <path d="M18 8l4 4-4 4"></path>
        </svg>
      </div>

      <div class="grid">
        <a class="btn" id="btn-google" href="/auth/google/login" aria-label="Continue with Google" title="Continue with Google">
          <span class="ico google" role="img" aria-label="Google"></span>
        </a>
        <a class="btn" id="btn-discord" href="/auth/discord/login" aria-label="Continue with Discord" title="Continue with Discord">
          <span class="ico discord" role="img" aria-label="Discord"></span>
        </a>
      </div>

      <div class="stripes" aria-hidden="true">
        <div class="stripe"></div>
        <div class="stripe"></div>
      </div>

      <small class="muted">By continuing, you agree to our Terms &amp; Privacy Policy.</small>
    </div>
  </div>
</body>
</html>
"""
    )


@router.get("/google/login")
async def login_via_google(req: Request):
    if req.session.get(ACCOUNT, None):
        return RedirectResponse(url="/", status_code=303)
        
    return await google.authorize_redirect(
        req,
        req.url_for('auth_via_google'),
        prompt="none",
    )


@router.get("/google")
async def auth_via_google(req: Request,  q: Repository):
    if req.query_params.get("error"):
        return await google.authorize_redirect(
            req,
            req.url_for("auth_via_google"),
        )

    token = await google.authorize_access_token(req)
    usr = token['userinfo']
    account = Account(
        provider=Provider.GOOGLE,
        subject=usr.get("sub"),
        email=usr.get("email"),
    ).model_dump()

    req.session[ACCOUNT] = account
    await q.upsert_account(**account)

    return RedirectResponse(url="/", status_code=303)


@router.get("/discord/login")
async def login_via_discord(req: Request):
    if req.session.get(ACCOUNT, None):
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
    client = httpx.AsyncClient()
    resp = await client.get('https://discord.com/api/users/@me', headers={'Authorization': f'Bearer {token["access_token"]}'})

    usr = resp.json()
    account = Account(
        provider=Provider.DISCORD,
        subject=usr.get("id"),
        email=usr.get("email")
    ).model_dump()

    await q.upsert_account(**account)
    req.session[ACCOUNT] = account

    return RedirectResponse(url="/", status_code=303)
