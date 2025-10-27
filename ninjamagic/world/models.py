import numpy as np

from ninjamagic.world.state import demo_chipset

glyphs = np.array([chr(t[2]) for t in demo_chipset], dtype=object)


def _ser(v: np.ndarray) -> str:
    chars = glyphs[v]
    lines = ["".join(row) for row in chars]
    return "\n".join(lines)
