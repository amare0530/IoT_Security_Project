import numpy as np

from puf.bit_selection import select_stable_bits


def test_select_stable_bits() -> None:
    result = select_stable_bits([0.99, 0.75, 0.95], threshold=0.90)
    assert result.selected_count == 2
    assert np.array_equal(result.mask, np.array([True, False, True]))
