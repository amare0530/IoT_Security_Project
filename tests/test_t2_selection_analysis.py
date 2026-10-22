import numpy as np
import pandas as pd

from scripts.t2_selection_analysis import (
    find_deterministic_rows,
    leave_one_out_p1,
    select_positions,
)


def test_deterministic_rows_and_non_deterministic_selection() -> None:
    devices, rows, bits_per_row = 10, 10, 400
    rng = np.random.default_rng(4)
    goldens = rng.integers(0, 2, size=(devices, rows * bits_per_row), dtype=np.uint8)
    goldens[:, :bits_per_row] = 1
    distances = pd.DataFrame(
        {
            "row": range(rows),
            "mean_distance": [0.0] + [0.5] * (rows - 1),
            "min_distance": [0.0] * rows,
            "max_distance": [0.0] * rows,
        }
    )
    deterministic = find_deterministic_rows(distances, 0.01)
    assert deterministic == {0}

    p1 = leave_one_out_p1(goldens, 0)
    assert np.array_equal(p1, np.delete(goldens, 0, axis=0).mean(axis=0))
    mask = np.ones(goldens.shape[1], dtype=np.uint8)
    selected = select_positions(mask, p1, deterministic, bits_per_row, 2816)
    assert len(selected) == 2816
    assert not np.any(selected < bits_per_row)


def test_leave_one_out_excludes_self_and_cap_is_respected() -> None:
    goldens = np.zeros((3, 40), dtype=np.uint8)
    goldens[0] = 1
    assert np.all(leave_one_out_p1(goldens, 0) == 0)
    mask = np.ones(40, dtype=np.uint8)
    selected = select_positions(
        mask, leave_one_out_p1(goldens, 0), set(), 10, 12, per_row_cap=3
    )
    assert len(selected) == 12
    assert all(np.count_nonzero(selected // 10 == row) <= 3 for row in range(4))


def test_a_selection_can_have_zero_attacker_key_errors() -> None:
    bits_per_group = 11
    goldens = np.zeros((3, 2816), dtype=np.uint8)
    p1 = leave_one_out_p1(goldens, 0)
    assert np.all(p1 == 0)
    assert np.all((p1 >= 0.5) == goldens[0])
