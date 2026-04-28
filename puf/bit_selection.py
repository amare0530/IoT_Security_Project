from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import numpy as np


@dataclass(frozen=True)
class BitSelectionResult:
    mask: np.ndarray
    selected_count: int


def select_stable_bits(stability_scores: Iterable[float], threshold: float) -> BitSelectionResult:
    scores = np.array(list(stability_scores), dtype=float)
    mask = scores >= threshold
    return BitSelectionResult(mask=mask, selected_count=int(mask.sum()))
