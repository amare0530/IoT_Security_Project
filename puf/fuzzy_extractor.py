from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class GenOutput:
    key_bits: str
    helper_data: str


class FuzzyExtractor:
    """Lightweight XOR-based fuzzy extractor demo implementation."""

    def gen(self, puf_bits: str, key_bits: str) -> GenOutput:
        if len(puf_bits) != len(key_bits):
            raise ValueError("puf_bits and key_bits must have equal length")
        helper = "".join("1" if a != b else "0" for a, b in zip(puf_bits, key_bits))
        return GenOutput(key_bits=key_bits, helper_data=helper)

    def rep(self, noisy_bits: str, helper_data: str) -> str:
        if len(noisy_bits) != len(helper_data):
            raise ValueError("noisy_bits and helper_data must have equal length")
        reconstructed = "".join(
            "1" if a != b else "0" for a, b in zip(noisy_bits, helper_data)
        )
        return reconstructed
