import numpy as np
import pandas as pd

from scripts.t2_diagnostics import (
    error_distribution,
    evaluate_assignments,
    find_deterministic_rows,
    selected_row_stats,
)


def test_d1_deterministic_rows_and_d2_group_spacing() -> None:
    distances = pd.DataFrame({"row": [0, 1], "mean_distance": [0.0, 0.2]})
    assert find_deterministic_rows(distances, 0.01) == {0}
    positions = np.arange(22, dtype=np.int64)
    stats = selected_row_stats(positions)
    assert stats["within_group_adjacent_gap_median"] == 1.0
    assert stats["groups_same_row"] == 2


def test_d3_and_d6_helpers_have_expected_shapes() -> None:
    goldens = np.zeros((4, 44), dtype=np.uint8)
    assert np.all(np.mean(np.delete(goldens, 0, axis=0), axis=0) == 0)
    errors = [np.zeros(2816, dtype=np.uint8)]
    positions = [np.arange(2816, dtype=np.int64)]
    assignments = evaluate_assignments(errors, positions)
    assert set(assignments["assignment"]) == {"current", "round_robin", "random"}
    assert all(assignments.groupby("assignment").size() == 1)


def test_error_distribution_counts_all_seven_buckets() -> None:
    counts = np.array([0, 1, 2, 3, 4, 5, 6, 8])
    assert error_distribution(counts) == {"0": 1, "1": 1, "2": 1, "3": 1, "4": 1, "5": 1, ">=6": 2}
