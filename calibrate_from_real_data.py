"""
Real-data calibration helper for PUFConfig.

Goal:
- Input average BER from open SRAM PUF datasets.
- Estimate a practical noise_sigma for PUFConfig.
- Provide a short calibration report and optional JSON export.
"""

from __future__ import annotations

import json
import math
import os
from dataclasses import dataclass, asdict
from typing import Optional


@dataclass
class CalibrationResult:
    dataset_name: str
    avg_ber: float
    sample_count: Optional[int]
    confidence: float
    z_score: float
    ber_ci_low: float
    ber_ci_high: float
    suggested_noise_sigma: float
    suggested_noise_sigma_low: float
    suggested_noise_sigma_high: float
    note: str


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def ber_to_noise_sigma(avg_ber: float, calibration_gain: float = 1.0) -> float:
    """
    Map average BER to simulator noise_sigma.

    For this simulator, first-order approximation is:
      noise_sigma ~= BER * calibration_gain

    calibration_gain lets you compensate when measured BER includes
    additional effects (temperature drift, readout path noise, etc.).
    """
    if not (0.0 <= avg_ber <= 1.0):
        raise ValueError("avg_ber must be in [0, 1]")
    if calibration_gain <= 0:
        raise ValueError("calibration_gain must be > 0")

    return _clamp(avg_ber * calibration_gain, 0.001, 0.50)


def calibrate_from_avg_ber(
    avg_ber: float,
    dataset_name: str = "external_sram_puf_dataset",
    sample_count: Optional[int] = None,
    confidence: float = 0.95,
    calibration_gain: float = 1.0,
) -> CalibrationResult:
    """
    Estimate noise_sigma and confidence interval from BER.

    CI model:
      p_hat +/- z * sqrt(p_hat*(1-p_hat)/n)
    (binomial approximation when sample_count is available)
    """
    if confidence != 0.95:
        raise ValueError("Only 95% confidence is currently supported")

    z_score = 1.96
    sigma = ber_to_noise_sigma(avg_ber, calibration_gain=calibration_gain)

    if sample_count is None or sample_count <= 0:
        ber_low = avg_ber
        ber_high = avg_ber
        sigma_low = sigma
        sigma_high = sigma
        note = "No sample_count provided; CI collapsed to point estimate"
    else:
        std_err = math.sqrt(avg_ber * (1.0 - avg_ber) / sample_count)
        ber_low = _clamp(avg_ber - z_score * std_err, 0.0, 1.0)
        ber_high = _clamp(avg_ber + z_score * std_err, 0.0, 1.0)
        sigma_low = ber_to_noise_sigma(ber_low, calibration_gain=calibration_gain)
        sigma_high = ber_to_noise_sigma(ber_high, calibration_gain=calibration_gain)
        note = "95% CI estimated with binomial approximation"

    return CalibrationResult(
        dataset_name=dataset_name,
        avg_ber=avg_ber,
        sample_count=sample_count,
        confidence=confidence,
        z_score=z_score,
        ber_ci_low=ber_low,
        ber_ci_high=ber_high,
        suggested_noise_sigma=sigma,
        suggested_noise_sigma_low=sigma_low,
        suggested_noise_sigma_high=sigma_high,
        note=note,
    )


def save_calibration_result(result: CalibrationResult, out_path: str) -> None:
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(asdict(result), f, indent=2, ensure_ascii=False)


def _demo() -> None:
    """Quick demo with two public SRAM-PUF style BER assumptions."""
    examples = [
        ("Zenodo_SRAM_Based_PUF_Readouts", 0.020, 120000),
        ("IEEE_IoT_Swarm_SRAM", 0.035, 50000),
    ]

    print("Calibration demo (BER -> noise_sigma)")
    for name, ber, n in examples:
        result = calibrate_from_avg_ber(ber, dataset_name=name, sample_count=n)
        print(
            f"- {name}: BER={result.avg_ber:.4f} => noise_sigma={result.suggested_noise_sigma:.4f} "
            f"(95% CI {result.suggested_noise_sigma_low:.4f}~{result.suggested_noise_sigma_high:.4f})"
        )


if __name__ == "__main__":
    _demo()
