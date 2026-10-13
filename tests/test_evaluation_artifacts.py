import json
from pathlib import Path

import pandas as pd

from analysis.inter_hd import compute_and_plot_inter_hd
from experiments.evaluation import summarize_thresholds, write_evaluation


def test_inter_hd_persists_explicit_cohort_artifacts(tmp_path: Path) -> None:
    masks = [
        {"uid": "a", "threshold": 0.9, "mask": "1111"},
        {"uid": "b", "threshold": 0.9, "mask": "1111"},
    ]
    masks_path = tmp_path / "masks.json"
    masks_path.write_text(json.dumps(masks), encoding="utf-8")
    stability_path = tmp_path / "stability.csv"
    pd.DataFrame(
        [
            {"uid": "a", "bit_position": 0, "dominant_bit": 0},
            {"uid": "a", "bit_position": 1, "dominant_bit": 0},
            {"uid": "a", "bit_position": 2, "dominant_bit": 1},
            {"uid": "a", "bit_position": 3, "dominant_bit": 1},
            {"uid": "b", "bit_position": 0, "dominant_bit": 1},
            {"uid": "b", "bit_position": 1, "dominant_bit": 0},
            {"uid": "b", "bit_position": 2, "dominant_bit": 0},
            {"uid": "b", "bit_position": 3, "dominant_bit": 1},
        ]
    ).to_csv(stability_path, index=False)

    output_dir = tmp_path / "inter-hd"
    result = compute_and_plot_inter_hd(masks_path, stability_path, cohort=["a", "b"], output_dir=output_dir)

    assert len(result) == 2
    summary = json.loads((output_dir / "inter_hd_summary.json").read_text(encoding="utf-8"))
    assert summary["device_count"] == 2
    assert summary["ordered_pair_count"] == 2
    assert (output_dir / "inter_hd.csv").exists()
    assert (output_dir / "inter_hd_dist.png").exists()


def test_evaluation_writes_summary_chart_and_manifest(tmp_path: Path) -> None:
    thresholds = tmp_path / "thresholds.csv"
    pd.DataFrame(
        [
            {"uid": "a", "threshold": 0.9, "selected_bits_count": 20, "estimated_ber_holdout": 0.1},
            {"uid": "b", "threshold": 0.9, "selected_bits_count": 22, "estimated_ber_holdout": 0.2},
            {"uid": "a", "threshold": 0.95, "selected_bits_count": 18, "estimated_ber_holdout": 0.05},
        ]
    ).to_csv(thresholds, index=False)

    output_dir = tmp_path / "evaluation"
    write_evaluation(output_dir, thresholds, None, None, seed=7)

    assert summarize_thresholds(thresholds)["devices"].tolist() == [2, 1]
    assert (output_dir / "threshold_summary.csv").exists()
    assert (output_dir / "threshold_vs_ber.png").exists()
    assert json.loads((output_dir / "evaluation_manifest.json").read_text(encoding="utf-8"))["random_seed"] == 7
