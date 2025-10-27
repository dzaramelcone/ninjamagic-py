import numpy as np

from ninjamagic.world.service import CellState, box_sum, generation

LIVE = CellState.LIVE.value
DEFAULT = CellState.DEFAULT.value


def test_box_sum_r0_identity_values():
    g = np.array([[1, 2], [3, 4]], dtype=np.uint8)
    out = box_sum(g, r=0)
    # Don’t enforce dtype; just values
    np.testing.assert_array_equal(out, g)


def test_box_sum_single_center_one_r1_all_ones():
    g = np.zeros((3, 3), dtype=np.uint8)
    g[1, 1] = 1
    out = box_sum(g, r=1)

    expected = np.ones((3, 3), dtype=np.uint64)
    np.testing.assert_array_equal(out, expected)


def test_box_sum_checkerboard_r1():
    g = np.array([[1, 0, 1], [0, 1, 0], [1, 0, 1]], dtype=np.uint8)
    out = box_sum(g, r=1)
    expected = np.array([[2, 3, 2], [3, 5, 3], [2, 3, 2]], dtype=np.uint64)
    np.testing.assert_array_equal(out, expected)


def test_box_sum_ones_5x5_r2_counts():
    g = np.ones((5, 5), dtype=np.uint8)
    out = box_sum(g, r=2)
    expected = np.array(
        [
            [9, 12, 15, 12, 9],
            [12, 16, 20, 16, 12],
            [15, 20, 25, 20, 15],
            [12, 16, 20, 16, 12],
            [9, 12, 15, 12, 9],
        ],
        dtype=np.uint64,
    )
    np.testing.assert_array_equal(out, expected)


def test_box_sum_all_ones_r1_known_counts():
    g = np.ones((3, 3), dtype=np.uint8)
    out = box_sum(g, r=1)

    expected = np.array([[4, 6, 4], [6, 9, 6], [4, 6, 4]], dtype=np.uint64)
    np.testing.assert_array_equal(out, expected)


def test_box_sum_asymmetry_guard_line_pattern():
    g = np.zeros((7, 7), dtype=np.uint8)
    g[3, :] = 1
    out = box_sum(g, r=1)
    np.testing.assert_array_equal(out[0, :], out[-1, :])
    np.testing.assert_array_equal(out[1, :], out[-2, :])


def test_box_sum_small_grid_large_radius_whole_sum_everywhere():
    g = np.array([[1, 2], [3, 4]], dtype=np.uint8)
    out = box_sum(g, r=10)
    expected_total = np.uint64(10)
    expected = np.full_like(out, expected_total)
    np.testing.assert_array_equal(out, expected)


def test_box_sum_neighbors_only_manual_counts():
    g = np.array([[0, 1, 0], [1, 1, 0], [0, 0, 0]], dtype=np.uint8)

    neighborhood_sum = box_sum(g, r=1)
    neighbors_only = neighborhood_sum - g  # center-inclusive -> minus self

    expected_neighbors = np.array([[3, 2, 2], [2, 2, 2], [2, 2, 1]], dtype=np.uint64)
    np.testing.assert_array_equal(neighbors_only, expected_neighbors)


def test_box_sum_symmetry_detects_directional_bias():
    g = np.zeros((5, 5), dtype=np.uint8)
    g[2, :] = 1
    g[:, 2] = 1
    out = box_sum(g, r=1)

    np.testing.assert_array_equal(out, out[::-1, :])  # vertical symmetry
    np.testing.assert_array_equal(out, out[:, ::-1])  # horizontal symmetry


# Conway's Game of Life via ca_generation

LIVE = CellState.LIVE.value
DEAD = CellState.DEAD.value
DEFAULT = CellState.DEFAULT.value
ALWAYS = CellState.ALWAYS_ALIVE.value


def _life_step(grid: np.ndarray, *, steps: int = 1):
    for _ in range(steps):
        generation(grid, birth=[3], survive=[2, 3], radius=1)
    return grid == LIVE


def test_single_live_cell_dies_because_underpopulation():
    g = np.full((3, 3), DEFAULT, dtype=np.uint8)
    g[1, 1] = LIVE
    generation(g, birth=[3], survive=[2, 3], radius=1)
    assert g[1, 1] == DEAD


def test_three_in_a_row_births_in_center_and_ends_corners():
    g = np.full((5, 5), DEFAULT, dtype=np.uint8)
    g[2, 1] = g[2, 2] = g[2, 3] = LIVE
    generation(g, birth=[3], survive=[2, 3], radius=1)
    live = g == LIVE
    expected = np.zeros((5, 5), dtype=bool)
    expected[1, 2] = expected[2, 2] = expected[3, 2] = True
    np.testing.assert_array_equal(live, expected)


def test_always_alive_never_changes_and_counts_as_neighbor():
    g = np.full((3, 3), DEFAULT, dtype=np.uint8)
    g[1, 1] = ALWAYS
    g[1, 2] = LIVE
    generation(g, birth=[3], survive=[2, 3], radius=1)
    assert g[1, 1] == ALWAYS
    assert g[1, 2] != LIVE


def test_radius2_birth_full_board_expected():
    g = np.full((5, 5), DEFAULT, dtype=np.uint8)
    g[0, 2] = LIVE
    g[2, 0] = LIVE
    g[4, 2] = LIVE

    generation(g, birth=[3], survive=[2, 3], radius=2)

    expected = np.zeros((5, 5), dtype=bool)
    expected[2, 0] = True
    expected[2, 1] = True
    expected[2, 2] = True
    np.testing.assert_array_equal(g == LIVE, expected)


def test_still_life_block_stays_the_same():
    g = np.full((4, 4), DEFAULT, dtype=np.uint8)
    g[1, 1] = LIVE
    g[1, 2] = LIVE
    g[2, 1] = LIVE
    g[2, 2] = LIVE

    data = _life_step(g.copy(), steps=1)

    expected = np.zeros((4, 4), dtype=bool)
    expected[1, 1] = True
    expected[1, 2] = True
    expected[2, 1] = True
    expected[2, 2] = True

    np.testing.assert_array_equal(data, expected)


def test_oscillator_blinker_flips_orientation_each_step():
    g = np.full((5, 5), DEFAULT, dtype=np.uint8)
    g[2, 1] = LIVE
    g[2, 2] = LIVE
    g[2, 3] = LIVE

    # after 1 step: vertical
    data = _life_step(g.copy(), steps=1)
    expected1 = np.zeros((5, 5), dtype=bool)
    expected1[1, 2] = True
    expected1[2, 2] = True
    expected1[3, 2] = True
    np.testing.assert_array_equal(data, expected1)

    # after 2 steps: back to horizontal
    data = _life_step(g.copy(), steps=2)
    expected2 = np.zeros((5, 5), dtype=bool)
    expected2[2, 1] = True
    expected2[2, 2] = True
    expected2[2, 3] = True
    np.testing.assert_array_equal(data, expected2)


def test_glider_moves_down_right_after_four_steps():
    g = np.full((6, 6), DEFAULT, dtype=np.uint8)
    # glider in top-left:
    # . # .
    # . . #
    # # # #
    g[0, 1] = LIVE
    g[1, 2] = LIVE
    g[2, 0] = LIVE
    g[2, 1] = LIVE
    g[2, 2] = LIVE

    data = _life_step(g.copy(), steps=4)

    # after 4 generations a glider shifts +1,+1
    expected = np.zeros((6, 6), dtype=bool)
    expected[1, 2] = True
    expected[2, 3] = True
    expected[3, 1] = True
    expected[3, 2] = True
    expected[3, 3] = True

    np.testing.assert_array_equal(data, expected)
