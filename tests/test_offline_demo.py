from pathlib import Path

from scripts.run_offline_demo import run


def test_offline_demo_is_self_contained(tmp_path: Path) -> None:
    result = run(tmp_path / "demo")

    assert result["bits_available"] >= result["bits_consumed"] == 2816
    auth = result["authentication"]
    assert auth["valid"] is True
    assert auth["replay_valid"] is False
    assert auth["unknown_uid_valid"] is False
    assert (tmp_path / "demo" / "synthetic_sram.csv").exists()
    assert (tmp_path / "demo" / "demo_result.json").exists()
