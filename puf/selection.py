from __future__ import annotations

from typing import Literal

import numpy as np

from puf.fuzzy_extractor import FuzzyExtractor


def select_balanced_positions(
    stable_mask: np.ndarray,
    p1_others: np.ndarray,
    deterministic_rows: set[int],
    bits_per_row: int,
    count: int,
    rng: np.random.Generator,
) -> np.ndarray:
    if stable_mask.shape != p1_others.shape:
        raise ValueError("stable_mask and p1_others must have the same shape")
    if count <= 0:
        raise ValueError("count must be positive")
    candidates = np.flatnonzero(stable_mask == 1)
    candidates = np.asarray(
        [index for index in candidates if index // bits_per_row not in deterministic_rows],
        dtype=np.int64,
    )
    if len(candidates) < count:
        raise ValueError(f"only {len(candidates)} balanced candidates; need {count}")
    order = np.lexsort(
        (rng.random(len(candidates)), np.abs(p1_others[candidates] - 0.5))
    )
    return np.sort(candidates[order[:count]])


def _reorder_indices(
    count: int, order: Literal["round_robin", "random"], rng: np.random.Generator | None
) -> np.ndarray:
    if count % 256 != 0:
        raise ValueError("selected position count must be divisible by 256")
    sorted_indices = np.arange(count, dtype=np.int64)
    if order == "round_robin":
        return np.concatenate(
            [sorted_indices[group::256] for group in range(256)]
        )
    if order == "random":
        if rng is None:
            raise ValueError("rng is required for random order")
        return rng.permutation(sorted_indices)
    raise ValueError(f"unsupported order: {order}")


def reorder_helper_data(
    golden: np.ndarray,
    key: bytes,
    helper: dict,
    order: Literal["round_robin", "random"],
    rng: np.random.Generator | None = None,
) -> dict:
    extractor = FuzzyExtractor(
        bits_needed=int(helper["bits_needed"]),
        repetition=int(helper["repetition"]),
    )
    original_positions = np.asarray(helper["stable_indices"], dtype=np.int64)
    encoded = np.asarray(helper["W"], dtype=np.uint8)
    if len(original_positions) != extractor.total_bits_required:
        raise ValueError("helper stable_indices length does not match extractor")
    original_codeword = encoded ^ golden[original_positions]
    key_bits = extractor._majority_vote_with_params(
        original_codeword, extractor.bits_needed, extractor.repetition
    )
    permutation = _reorder_indices(len(original_positions), order, rng)
    new_positions = original_positions[permutation]
    new_codeword = np.repeat(key_bits, extractor.repetition)
    new_helper = dict(helper)
    new_helper["stable_indices"] = new_positions.tolist()
    new_helper["W"] = (new_codeword ^ golden[new_positions]).tolist()
    if extractor.rep(golden, new_helper) != key:
        raise ValueError("reordered helper does not reconstruct the enrollment key")
    return new_helper
