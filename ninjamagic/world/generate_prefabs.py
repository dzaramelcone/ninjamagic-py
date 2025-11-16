import random

EIGHT_DIRS = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]
BIRTH = {5, 6, 7}
SURVIVE = {4, 5, 6, 7}
SIZE = (16, 16)
LUT = [".", "#"]


def game_of_life(grid: memoryview) -> memoryview:
    if not grid.shape:
        raise ValueError
    h, w = grid.shape

    def is_alive(y: int, x: int) -> bool:
        if 0 <= y < h and 0 <= x < w:
            return grid[y, x] == 1
        return True

    new = memoryview(bytearray(h * w)).cast("B", (h, w))
    pts = [(y, x) for y in range(h) for x in range(w)]
    for y, x in pts:
        alive = is_alive(y, x)
        pop = sum(is_alive(y + dy, x + dx) for dy, dx in EIGHT_DIRS)
        if alive and pop in SURVIVE or not alive and pop in BIRTH:
            new[y, x] = 1

    for y in range(SIZE[0]):
        for x in (0, SIZE[1] - 1):
            new[y, x] = 1
    for y in (0, SIZE[0] - 1):
        for x in range(SIZE[1]):
            new[y, x] = 1

    return new


def generate_prefabs():
    rng = random.Random()
    out = bytearray()
    appends = SIZE[0] * SIZE[1] * 32 * 32
    while len(out) < appends:
        base = memoryview(
            bytearray(
                [0 if rng.random() < 0.575 else 1 for _ in range(SIZE[0] * SIZE[1])]
            )
        ).cast("B", SIZE)
        game = base
        for _ in range(10):
            game = game_of_life(game)
        for y in range(SIZE[0]):
            print("".join([LUT[game[y, x]] for x in range(SIZE[1])]))
        out.extend(game.cast("B"))

    with open("prefabs.bin", "wb") as fw:
        fw.write(out)
