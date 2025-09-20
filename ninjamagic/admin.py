import logging
from fastapi import APIRouter, Depends, HTTPException, Request
import os
import time

from ninjamagic.auth import admin_owner_challenge


TRIGGER = "/var/lib/ninjamagic/deploy.trigger"

router = APIRouter(prefix="/admin", dependencies=[Depends(admin_owner_challenge)])
log = logging.getLogger(__name__)


@router.get("/deploy")
async def deploy(req: Request):
    if not os.access(TRIGGER, mode=os.W_OK):
        raise HTTPException(status_code=404, detail="Trigger not found")

    with open(TRIGGER, "w") as f:
        f.write(str(time.time()))
