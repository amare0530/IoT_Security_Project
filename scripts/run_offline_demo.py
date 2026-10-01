"""Run the SRAM-PUF -> FE -> HMAC demo without a broker or private data."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from analysis.stability_analysis import load_dataset, sample_level_bit_matrix
from auth.hmac_auth import PUFAuthenticator
from fixtures.demo_data import rows
from mqtt.device import build_response_payload
from mqtt.server import build_challenge_payload, extract_challenge
from puf.fuzzy_extractor import FuzzyExtractor


_MATRIX_CACHE: dict[tuple[str, int], dict[str, np.ndarray]] = {}


def write_fixture(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = ["board_type", "uid", "pic", "address", "data", "created_at"]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows())


def run(
    output_dir: Path,
    input_path: Path | None = None,
    include_private_context: bool = False,
) -> dict[str, object]:
    """Run the demo from a private dataset or the portable synthetic fixture."""
    output_dir.mkdir(parents=True, exist_ok=True)
    source_label = "synthetic fixture"
    if input_path is None:
        input_path = output_dir / "synthetic_sram.csv"
        write_fixture(input_path)
    else:
        input_path = Path(input_path)
        source_label = "local SRAM dataset"

    cache_key = (str(input_path.resolve()), input_path.stat().st_mtime_ns)
    matrices = _MATRIX_CACHE.get(cache_key)
    if matrices is None:
        dataset = load_dataset(input_path)
        matrices = sample_level_bit_matrix(dataset)
        _MATRIX_CACHE.clear()
        _MATRIX_CACHE[cache_key] = matrices
    if not matrices:
        raise ValueError("No device has at least two valid captures in the selected dataset")
    uid = sorted(matrices)[0]
    golden = (matrices[uid].mean(axis=0) >= 0.5).astype(np.uint8)
    stability = np.maximum(matrices[uid].mean(axis=0), 1 - matrices[uid].mean(axis=0))
    mask = (stability >= 0.90).astype(np.uint8)

    extractor = FuzzyExtractor(bits_needed=256, repetition=11)
    key, helper_data = extractor.gen(
        golden, mask, uid=uid, rng=np.random.default_rng(20260922)
    )

    noise_rng = np.random.default_rng()
    noisy_response = golden.copy()
    noise_flip_indices: list[int] = []
    stable_indices = np.asarray(helper_data["stable_indices"], dtype=np.int64)
    max_flips_per_group = extractor.repetition // 2
    for group_start in range(0, len(stable_indices), extractor.repetition):
        group_indices = stable_indices[group_start : group_start + extractor.repetition]
        flip_count = int(noise_rng.integers(1, min(3, max_flips_per_group) + 1))
        selected = noise_rng.choice(group_indices, size=flip_count, replace=False)
        noisy_response[selected] ^= 1
        noise_flip_indices.extend(int(index) for index in selected)

    reconstructed = extractor.rep(noisy_response, helper_data)

    authenticator = PUFAuthenticator(time_window_seconds=60)
    challenge_payload = build_challenge_payload(authenticator, uid)
    challenge = extract_challenge(challenge_payload)
    response = build_response_payload(authenticator, reconstructed, uid, challenge)
    valid, valid_message = authenticator.verify_response(key, uid, challenge, response["hmac"])
    replay_valid, replay_message = authenticator.verify_response(key, uid, challenge, response["hmac"])

    unknown_challenge = authenticator.generate_challenge()
    unknown_response = authenticator.generate_response(key, "unknown-device", unknown_challenge)
    unknown_valid, unknown_message = authenticator.verify_response(
        key, "expected-device", unknown_challenge, unknown_response
    )

    attack_challenge = authenticator.generate_challenge()
    attack_hmac = authenticator.generate_response(key, uid, attack_challenge)

    trace_rng = np.random.default_rng()
    helper_bits = np.asarray(helper_data["W"], dtype=np.uint8)
    selected_indices = stable_indices
    sample_size = min(32, len(selected_indices))
    sample_offsets = np.sort(
        trace_rng.choice(
            len(selected_indices), size=sample_size, replace=False
        )
    )
    sample_response_indices = selected_indices[sample_offsets]
    enrollment_bits = golden[sample_response_indices]
    noisy_bits = noisy_response[sample_response_indices]
    sample_noise_flip_positions = [
        offset
        for offset, (enrollment_bit, noisy_bit) in enumerate(zip(enrollment_bits, noisy_bits))
        if enrollment_bit != noisy_bit
    ]
    helper_sample = helper_bits[sample_offsets]
    corrected_sample = helper_sample ^ noisy_bits

    record = {
        "fixture": input_path.name,
        "source": source_label,
        "uid": uid,
        "bits_available": int(mask.sum()),
        "bits_consumed": extractor.total_bits_required,
        "helper_data": helper_data,
        "authentication": {
            "valid": valid,
            "message": valid_message,
            "replay_valid": replay_valid,
            "replay_message": replay_message,
            "unknown_uid_valid": unknown_valid,
            "unknown_uid_message": unknown_message,
        },
        "trace": {
            "chip_bit_count": int(len(golden)),
            "stable_bit_threshold": 0.90,
            "extractor_key_bits": extractor.bits_needed,
            "repetition": extractor.repetition,
            "stable_bits_consumed": extractor.total_bits_required,
            "sample_size": sample_size,
            "sample_response_indices": sample_response_indices.tolist(),
            "sample_enrollment_bits": "".join(map(str, enrollment_bits.tolist())),
            "sample_mask_bits": "".join(
                map(str, mask[sample_response_indices].tolist())
            ),
            "sample_noisy_bits": "".join(map(str, noisy_bits.tolist())),
            "noise_model": "bounded simulated noise",
            "noise_flip_count": len(noise_flip_indices),
            "noise_flip_positions": noise_flip_indices,
            "sample_noise_flip_positions": sample_noise_flip_positions,
            "sample_helper_bits": "".join(map(str, helper_sample.tolist())),
            "sample_xor_bits": "".join(map(str, corrected_sample.tolist())),
            "derived_key_bits": extractor.bits_needed,
            "hmac_key_bits": len(key) * 8,
            "hmac_key_fingerprint": hashlib.sha256(key).hexdigest()[:16],
            "challenge_payload": f"{uid}:{challenge['nonce']}:{challenge['timestamp']}",
            "hmac_tag": response["hmac"],
        },
    }
    if include_private_context:
        record["_private_context"] = {
            "key": key,
            "uid": uid,
            "challenge": challenge,
            "hmac": response["hmac"],
            "attack_challenge": attack_challenge,
            "attack_hmac": attack_hmac,
            "authenticator": authenticator,
        }
    public_record = {key: value for key, value in record.items() if not key.startswith("_")}
    with (output_dir / "demo_result.json").open("w", encoding="utf-8") as handle:
        json.dump(public_record, handle, indent=2)
    return record


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the offline synthetic SRAM-PUF demo")
    parser.add_argument("--output-dir", type=Path, default=Path("demo-output"))
    args = parser.parse_args()
    result = run(args.output_dir)
    print(json.dumps(result["authentication"], indent=2))
    if not result["authentication"]["valid"]:
        raise SystemExit("offline demo authentication failed")


if __name__ == "__main__":
    main()
