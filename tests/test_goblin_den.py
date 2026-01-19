from ninjamagic.util import TILE_STRIDE_H, TILE_STRIDE_W
from ninjamagic.world.goblin_den import (
    DEN_SIZE,
    find_open_spots,
    generate_den_prefab,
    stamp_den_prefab,
)


def test_generate_den_prefab_returns_8x8_bytearray():
    """Den prefab should be 64 bytes (8x8) of walkable (0) and wall (1) cells."""
    prefab = generate_den_prefab()

    assert isinstance(prefab, bytearray)
    assert len(prefab) == 64


def test_generate_den_prefab_contains_only_valid_values():
    """Prefab cells should only be 0 (walkable) or 1 (wall)."""
    prefab = generate_den_prefab()

    for cell in prefab:
        assert cell in (0, 1)


def test_generate_den_prefab_has_walkable_cells():
    """Den should have some walkable space."""
    prefab = generate_den_prefab()

    walkable_count = sum(1 for cell in prefab if cell == 0)
    assert walkable_count >= 8, "Den should have at least 8 walkable cells"


def test_stamp_den_prefab_only_copies_walkable_cells():
    """Stamp should only copy walkable cells, preserving existing terrain."""
    tile = bytearray([2] * 256)  # All walls initially
    prefab = bytearray([0] * 32 + [1] * 32)  # Top half walkable, bottom half wall
    lut = [1, 2]  # 0 -> 1 (floor), 1 -> 2 (wall)

    offset_y, offset_x = stamp_den_prefab(tile, prefab, lut)

    # Check that the prefab was stamped
    assert 0 <= offset_y <= TILE_STRIDE_H - DEN_SIZE
    assert 0 <= offset_x <= TILE_STRIDE_W - DEN_SIZE

    # Verify: walkable cells stamped, wall cells left unchanged
    tile_view = memoryview(tile).cast("B", (TILE_STRIDE_H, TILE_STRIDE_W))
    prefab_view = memoryview(prefab).cast("B", (DEN_SIZE, DEN_SIZE))
    for dy in range(DEN_SIZE):
        for dx in range(DEN_SIZE):
            if prefab_view[dy, dx] == 0:  # Walkable in prefab
                assert tile_view[offset_y + dy, offset_x + dx] == lut[0]
            else:  # Wall in prefab - tile unchanged
                assert tile_view[offset_y + dy, offset_x + dx] == 2


def test_stamp_den_prefab_returns_valid_offset():
    """Stamp should return offset within valid bounds."""
    tile = bytearray([1] * 256)
    prefab = generate_den_prefab()
    lut = [1, 2]

    for _ in range(20):
        offset_y, offset_x = stamp_den_prefab(tile.copy(), prefab, lut)
        assert 0 <= offset_y <= TILE_STRIDE_H - DEN_SIZE
        assert 0 <= offset_x <= TILE_STRIDE_W - DEN_SIZE


def test_find_open_spots_returns_walkable_cells():
    """Should return world coordinates of walkable cells in the stamped region."""
    tile = bytearray([2] * 256)  # All walls
    # Create a simple pattern: walkable at (0,0), (1,1), (2,2) in prefab coords
    prefab = bytearray([1] * 64)  # All walls
    prefab[0] = 0  # (0,0) walkable
    prefab[9] = 0  # (1,1) walkable
    prefab[18] = 0  # (2,2) walkable

    lut = [1, 2]  # 0 -> 1 (walkable), 1 -> 2 (wall)
    walkable_id = 1

    # Stamp at offset (2, 3)
    offset_y, offset_x = 2, 3
    tile_view = memoryview(tile).cast("B", (TILE_STRIDE_H, TILE_STRIDE_W))
    prefab_view = memoryview(prefab).cast("B", (DEN_SIZE, DEN_SIZE))
    for dy in range(DEN_SIZE):
        for dx in range(DEN_SIZE):
            tile_view[offset_y + dy, offset_x + dx] = lut[prefab_view[dy, dx]]

    spots = find_open_spots(tile, offset_y, offset_x, walkable_id)

    # Should find the 3 walkable cells, in world coordinates
    expected = [(2, 3), (3, 4), (4, 5)]
    assert sorted(spots) == sorted(expected)


def test_find_open_spots_returns_n_random_spots():
    """With n parameter, should return at most n random spots."""
    tile = bytearray([1] * 256)  # All walkable
    walkable_id = 1

    spots = find_open_spots(tile, 0, 0, walkable_id, n=5)

    assert len(spots) == 5
    for y, x in spots:
        assert 0 <= y < DEN_SIZE
        assert 0 <= x < DEN_SIZE
