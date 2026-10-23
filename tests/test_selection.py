import numpy as np

from puf.fuzzy_extractor import FuzzyExtractor
from puf.selection import reorder_helper_data, select_balanced_positions


def test_balanced_selection_excludes_rows_and_is_sorted() -> None:
    rng = np.random.default_rng(4)
    stable = np.ones(4000, dtype=np.uint8)
    p1 = np.linspace(0, 1, len(stable))
    positions = select_balanced_positions(stable, p1, {0}, 100, 2816, rng)
    assert len(positions) == 2816
    assert np.all(positions[:-1] < positions[1:])
    assert np.all(positions // 100 != 0)


def test_reordering_preserves_key_and_round_robin_spacing() -> None:
    extractor = FuzzyExtractor()
    golden = np.random.default_rng(7).integers(0, 2, 655360, dtype=np.uint8)
    mask = np.zeros_like(golden)
    mask[:2816] = 1
    key, helper = extractor.gen(golden, mask, "demo", np.random.default_rng(8))
    reordered = reorder_helper_data(golden, key, helper, "round_robin")
    positions = np.asarray(reordered["stable_indices"])
    groups = positions.reshape(256, 11)
    assert np.all(np.diff(groups, axis=1) % 256 == 0)
    assert extractor.rep(golden, reordered) == key


def test_random_reordering_is_reproducible_and_tolerates_noise() -> None:
    extractor = FuzzyExtractor()
    golden = np.random.default_rng(9).integers(0, 2, 655360, dtype=np.uint8)
    mask = np.zeros_like(golden)
    mask[:2816] = 1
    key, helper = extractor.gen(golden, mask, "demo", np.random.default_rng(10))
    first = reorder_helper_data(
        golden, key, helper, "random", np.random.default_rng(11)
    )
    second = reorder_helper_data(
        golden, key, helper, "random", np.random.default_rng(11)
    )
    assert first == second
    noisy = golden.copy()
    noisy[np.asarray(first["stable_indices"])[::11][:8]] ^= 1
    assert extractor.rep(noisy, first) == key
