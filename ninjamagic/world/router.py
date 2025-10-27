# ninjamagic/world/router.py
import json
from html import escape
from typing import Annotated

import numpy as np
from fastapi import APIRouter, Query
from fastapi.responses import HTMLResponse

from ninjamagic.world.service import generate_grid

router = APIRouter(prefix="/world")


def render_with_legend(buf: np.ndarray, legend_json: str | None) -> str:
    """
    Build an ASCII string from a uint8 grid using a legend mapping.
    - legend_json: JSON like {"0":" ", "1":".", "2":"#"} (keys int or str).
    - Default: base-256 mapping (chr(byte)).
    """
    mapping = [chr(i) for i in range(256)]
    if legend_json:
        try:
            raw = json.loads(legend_json)
            # Accept keys as str or int
            for k, v in raw.items():
                try:
                    idx = int(k)
                except (TypeError, ValueError):
                    continue
                if 0 <= idx <= 255:
                    mapping[idx] = str(v)
        except Exception:
            pass

    glyphs = np.array(mapping, dtype=object)
    chars = glyphs[buf]  # vectorized lookup
    return "\n".join("".join(row) for row in chars)


@router.get("/build", response_class=HTMLResponse)
async def build_world(
    w: Annotated[int, Query(gt=0, lt=1024)] = 64,
    h: Annotated[int, Query(gt=0, lt=1024)] = 64,
    seed: Annotated[int, Query()] = 1,
    iters: Annotated[int, Query(gt=0)] = 4,
    step: Annotated[int, Query(ge=0)] = 0,
    # New: rules & legend
    noise: Annotated[float, Query()] = 0.55,
    birth: Annotated[list[int], Query()] = [2],
    survive: Annotated[list[int], Query()] = [2, 3],
    legend: Annotated[str | None, Query()] = None,  # JSON dict
) -> HTMLResponse:
    buf = np.zeros((h, w), dtype=np.uint8)

    desc = ""
    # If/when your pipeline uses birth/survive, thread them through there.
    for gen_step, desc in generate_grid(
        grid=buf,
        seed=seed,  # iters=iters, birth=birth, survive=survive, noise=noise
    ):
        if step == gen_step:
            break

    ascii_map = render_with_legend(buf, legend)
    # Echo chosen rules for debugging
    info = f"Birth={birth} Survive={survive}"

    return HTMLResponse(
        f"<pre id='map'>{escape(desc)}\n{escape(info)}\n{escape(ascii_map)}\n</pre>"
    )


@router.get("", response_class=HTMLResponse)
async def world_page() -> HTMLResponse:
    return HTMLResponse(
        """
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8" />
  <script src="https://unpkg.com/htmx.org"></script>
  <style>
    body { background:#111; color:#eee; font: 16px/1.3 ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; margin:16px; }
    pre  {
      font: 32/1.3 ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
      letter-spacing: 20;
      margin-top:12px;
      white-space:pre; }
    label { margin-right:10px; }
    input[type=number] { width:6ch; background:#222; color:#eee; border:1px solid #444; }
    textarea { width: 40ch; height: 8em; background:#222; color:#eee; border:1px solid #444; }
    fieldset { border:1px solid #333; padding:8px; margin:8px 0; }
    legend { padding:0 6px; }
  </style>
</head>
<body>
  <form id="controls"
        hx-get="/world/build"
        hx-target="#map"
        hx-swap="outerHTML"
        hx-trigger="change load">
    <label>W <input type="number" name="w" value="64" min="1" max="1023"></label>
    <label>H <input type="number" name="h" value="64" min="1" max="1023"></label>
    <label>Seed <input type="number" name="seed" value="1"></label>
    <label>Iters <input type="number" name="iters" value="4" min="1"></label>
    <label>Step <input type="number" name="step" value="0" min="0"></label>
    <label>Noise <input type="number" name="noise" value="0.55" min="0.00" max="1.00" step="0.01"></label>
    <fieldset>
      <legend>Rules</legend>
      <div>Birth:
        """
        + "".join(
            f'<label><input type="checkbox" name="birth" value="{i}"> {i}</label>'
            for i in range(9)
        )
        + """
      </div>
      <div>Survive:
        """
        + "".join(
            f'<label><input type="checkbox" name="survive" value="{i}"> {i}</label>'
            for i in range(9)
        )
        + """
      </div>
    </fieldset>
    <fieldset>
      <legend>Legend</legend>
      <textarea name="legend">{"0":" ", "1":".", "2":"#"}</textarea>
    </fieldset>
  </form>

  <pre id="map">Loading…</pre>

</body>
</html>
"""
    )
