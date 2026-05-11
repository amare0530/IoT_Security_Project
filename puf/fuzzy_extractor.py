from __future__ import annotations

import hashlib
import json
import secrets
from pathlib import Path
from typing import Tuple

import numpy as np
import pandas as pd


class FuzzyExtractor:
    """
    Fuzzy Extractor — Code Offset Construction (Secure Sketch)。

    正確架構說明：
    ─────────────────────────────────────────────────────────────
    舊做法（錯）：對 PUF 原始位元做多數決 → 容錯幾乎為 0
    新做法（對）：先用隨機金鑰編碼，XOR PUF 位元產生 Helper Data，
                  Rep() 時用 Helper Data 還原後再多數決 → 可容忍 5 個錯誤

    Gen()：
      1. 隨機產生 256-bit 金鑰 K
      2. 將 K 以重複碼展開為 C（每個 bit 重複 repetition 次）
      3. Helper Data W = C XOR R（R 為 PUF 穩定位元）
      4. 公開儲存 W，保密 K

    Rep()：
      1. 讀取帶雜訊的 PUF 位元 R'
      2. C' = W XOR R'（因為 W = C XOR R，所以 C' ≈ C）
      3. 對 C' 做多數決還原 K'
      4. K' 應與 K 完全相同（容忍 floor(repetition/2) 個錯誤）
    ─────────────────────────────────────────────────────────────
    """

    def __init__(self, bits_needed: int = 256, repetition: int = 11):
        self.bits_needed = bits_needed
        self.repetition = repetition
        self.total_bits_required = bits_needed * repetition

    # ------------------------------------------------------------------
    # 公開介面
    # ------------------------------------------------------------------

    def gen(
        self,
        response_bits: np.ndarray,
        mask: np.ndarray,
        uid: str = "",
        rng: np.random.Generator | None = None,
    ) -> Tuple[bytes, dict]:
        """
        Gen()：從 Golden Response 產生 Key 和 Helper Data。

        Args:
            response_bits : 完整 bitstream（Golden，shape: [n_bits]）
            mask          : 同長度的 0/1 遮罩（1 = 穩定位元）
            uid           : 裝置 UID（用來確保不同裝置產生不同 key）
            rng           : 實驗模式用 seeded RNG；正式流程不傳入

        Returns:
            key         : 128-bit bytes（用於 HMAC）
            helper_data : 公開存放於 Server，Rep() 重建時使用
        """
        stable_bits = response_bits[mask == 1]

        if len(stable_bits) < self.total_bits_required:
            raise ValueError(
                f"穩定位元不足：需要 {self.total_bits_required}，"
                f"實際只有 {len(stable_bits)}"
            )

        # 1. 取出前 total_bits_required 個穩定位元作為 R
        R = stable_bits[: self.total_bits_required]

        # 2. 產生 enrollment secret K。正式流程使用不可預測亂數；
        #    simulate_all() 才傳入 seeded RNG 以便實驗重現。
        key_bits = self._generate_key_bits(rng)

        # 3. 將 K 以重複碼展開為 C
        #    例：K=[1,0], repetition=3 → C=[1,1,1,0,0,0]
        C = np.repeat(key_bits, self.repetition)

        # 4. Helper Data W = C XOR R（公開）
        W = (C ^ R).tolist()

        stable_indices = np.where(mask == 1)[0][: self.total_bits_required].tolist()

        helper_data = {
            "uid": uid,
            "stable_indices": stable_indices,
            "bits_needed": self.bits_needed,
            "repetition": self.repetition,
            "W": W,
        }

        key = self._bits_to_key(key_bits, uid)
        return key, helper_data

    def rep(self, response_bits: np.ndarray, helper_data: dict) -> bytes:
        """
        Rep()：用本次開機的 Response 和 Helper Data 重建 Key。

        Args:
            response_bits : 本次開機的完整 bitstream（可能帶雜訊）
            helper_data   : Gen() 產生的公開輔助資料

        Returns:
            key : 重建出的 128-bit bytes
        """
        indices = np.array(helper_data["stable_indices"])
        repetition = helper_data["repetition"]
        bits_needed = helper_data["bits_needed"]
        W = np.array(helper_data["W"], dtype=np.uint8)
        uid = helper_data.get("uid", "")

        # 1. 取出本次 PUF 位元 R'（可能帶雜訊）
        R_prime = response_bits[indices]

        return self._rep_from_selected_bits(R_prime, helper_data)

    def _rep_from_selected_bits(self, selected_bits: np.ndarray, helper_data: dict) -> bytes:
        repetition = helper_data["repetition"]
        bits_needed = helper_data["bits_needed"]
        W = np.array(helper_data["W"], dtype=np.uint8)
        uid = helper_data.get("uid", "")

        # 2. C' = W XOR R'
        #    若 R' ≈ R，則 C' ≈ C（接近全 0 或全 repetition）
        C_prime = W ^ selected_bits

        # 3. 多數決解碼，容忍 floor(repetition/2) 個錯誤
        corrected_key_bits = self._majority_vote_with_params(
            C_prime, bits_needed, repetition
        )

        return self._bits_to_key(corrected_key_bits, uid)

    # ------------------------------------------------------------------
    # 內部工具
    # ------------------------------------------------------------------

    @staticmethod
    def _majority_vote_with_params(
        bits: np.ndarray, n: int, rep: int
    ) -> np.ndarray:
        chunks = bits[: n * rep].reshape(n, rep)
        return (chunks.sum(axis=1) > rep / 2).astype(np.uint8)

    @staticmethod
    def _bits_to_key(bits: np.ndarray, uid: str = "") -> bytes:
        """位元陣列 + UID salt → SHA-256 → 取前 16 bytes = 128-bit key"""
        pad = (8 - len(bits) % 8) % 8
        padded = np.append(bits, np.zeros(pad, dtype=np.uint8))
        raw_bytes = np.packbits(padded).tobytes()
        salted = raw_bytes + uid.encode("utf-8")
        return hashlib.sha256(salted).digest()[:16]

    def _generate_key_bits(self, rng: np.random.Generator | None = None) -> np.ndarray:
        if rng is not None:
            return rng.integers(0, 2, size=self.bits_needed, dtype=np.uint8)

        n_bytes = (self.bits_needed + 7) // 8
        random_bytes = secrets.token_bytes(n_bytes)
        return np.unpackbits(np.frombuffer(random_bytes, dtype=np.uint8))[
            : self.bits_needed
        ].astype(np.uint8)


# ------------------------------------------------------------------
# 獨立執行：對所有裝置模擬 Gen + Rep，驗證 key 一致性
# ------------------------------------------------------------------

def simulate_all(
    masks_path: Path,
    stability_csv_path: Path,
    output_path: Path,
    threshold: float = 0.9,
    bits_needed: int = 256,
    repetition: int = 11,
    ber_test: float = 0.05,
    experiment_seed: int = 20260506,
    random_noise_trials: int = 100,
) -> None:
    fe = FuzzyExtractor(bits_needed=bits_needed, repetition=repetition)

    print("讀取 masks.json ...")
    with open(masks_path, encoding="utf-8") as f:
        masks_raw = json.load(f)

    masks = {
        m["uid"]: np.array(list(m["mask"]), dtype=np.uint8)
        for m in masks_raw
        if m["threshold"] == threshold
    }

    print("讀取 stability_summary.csv ...")
    stab = pd.read_csv(stability_csv_path, low_memory=False)

    results = []
    max_err = repetition // 2  # 理論最大可容忍錯誤數

    print(f"實驗模式：使用固定 experiment_seed={experiment_seed} 產生可重現 enrollment key")
    print("雜訊模型 A：在 FE 使用位元上注入可校正的分散 BER")
    print(f"雜訊模型 B：純隨機 BER Monte Carlo，每台裝置 {random_noise_trials} 次")
    print(f"\n設定：repetition={repetition}，理論最大容錯={max_err} bits/group，BER={ber_test*100:.0f}%")
    print(
        f"{'UID (Short)':<22} | {'Key (Hex)':<18} | {'No-Noise':<10} | "
        f"{'Correctable':<11} | {'Random MC':<10}"
    )
    print("-" * 85)

    for uid, mask in masks.items():
        uid_data = stab[stab["uid"] == uid].sort_values("bit_position")
        if uid_data.empty:
            continue

        # Golden Response = dominant_bit（最穩定時的值）
        golden = uid_data["dominant_bit"].to_numpy(dtype=np.uint8)

        try:
            enrollment_seed = _seed_from_uid(uid, experiment_seed)
            enrollment_rng = np.random.default_rng(enrollment_seed)
            key_gen, helper_data = fe.gen(golden, mask, uid=uid, rng=enrollment_rng)
        except ValueError as e:
            print(f"  [skip] {uid[:20]}... → {e}")
            continue

        # 測試 1：無雜訊（Rep 應完全還原）
        key_rep = fe.rep(golden, helper_data)
        no_noise_ok = key_gen == key_rep

        # 測試 2：模擬 BER 雜訊（每個裝置用不同 seed）
        noisy = golden.copy()
        rng = np.random.default_rng(enrollment_seed + 1)  # +1 避免跟 gen() 用同一個 seed
        flip_idx = _correctable_noise_indices(
            stable_indices=np.array(helper_data["stable_indices"]),
            bits_needed=bits_needed,
            repetition=repetition,
            ber_test=ber_test,
            rng=rng,
        )
        noisy[flip_idx] ^= 1
        key_noisy = fe.rep(noisy, helper_data)
        ber_ok = key_gen == key_noisy

        random_success_rate = _random_noise_success_rate(
            fe=fe,
            golden=golden,
            helper_data=helper_data,
            expected_key=key_gen,
            ber_test=ber_test,
            trials=random_noise_trials,
            rng=np.random.default_rng(enrollment_seed + 2),
        )

        results.append(
            {
                "uid": uid,
                "key_hex": key_gen.hex(),
                "rep_consistent_no_noise": no_noise_ok,
                f"rep_consistent_{int(ber_test*100)}pct_ber": ber_ok,
                f"random_{int(ber_test*100)}pct_ber_success_rate": random_success_rate,
                f"random_{int(ber_test*100)}pct_ber_trials": random_noise_trials,
                "stable_bits_available": int(mask.sum()),
                "stable_bits_consumed": len(helper_data["stable_indices"]),
            }
        )

        print(
            f"  {uid[:20]}... | {key_gen.hex()[:16]}... | "
            f"{'OK' if no_noise_ok else 'FAIL':<10} | "
            f"{'OK' if ber_ok else 'FAIL':<11} | {random_success_rate*100:>8.1f}%"
        )

    df = pd.DataFrame(results)
    df.to_csv(output_path, index=False)

    total = len(df)
    if total == 0:
        print("沒有任何裝置成功處理。")
        return

    no_noise_rate = df["rep_consistent_no_noise"].mean() * 100
    ber_col = f"rep_consistent_{int(ber_test*100)}pct_ber"
    random_col = f"random_{int(ber_test*100)}pct_ber_success_rate"
    ber_rate = df[ber_col].mean() * 100
    random_rate = df[random_col].mean() * 100

    print(f"\n=== 結果摘要 ===")
    print(f"成功裝置數        : {total}")
    print(f"無雜訊一致性      : {df['rep_consistent_no_noise'].sum()}/{total}  ({no_noise_rate:.1f}%)")
    print(f"可校正 {ber_test*100:.0f}% BER : {df[ber_col].sum()}/{total}  ({ber_rate:.1f}%)")
    print(f"隨機 {ber_test*100:.0f}% BER MC : 平均 {random_rate:.1f}%  ({random_noise_trials} trials/device)")
    print(f"結果已儲存        : {output_path}")


def _seed_from_uid(uid: str, experiment_seed: int) -> int:
    seed_material = f"{experiment_seed}:{uid}".encode("utf-8")
    return int.from_bytes(hashlib.sha256(seed_material).digest()[:8], "big")


def _correctable_noise_indices(
    stable_indices: np.ndarray,
    bits_needed: int,
    repetition: int,
    ber_test: float,
    rng: np.random.Generator,
) -> np.ndarray:
    n_flip = int(len(stable_indices) * ber_test)
    max_correctable_per_group = repetition // 2
    max_correctable_total = bits_needed * max_correctable_per_group

    if n_flip > max_correctable_total:
        raise ValueError(
            f"BER={ber_test:.3f} requires {n_flip} flips, "
            f"but repetition={repetition} can correct at most {max_correctable_total}"
        )

    shuffled_groups = rng.permutation(bits_needed)
    group_counts = np.zeros(bits_needed, dtype=np.uint8)
    selected_positions = []

    for i in range(n_flip):
        group = int(shuffled_groups[i % bits_needed])
        if group_counts[group] >= max_correctable_per_group:
            raise ValueError("Noise injection exceeded the correction capacity")

        used_offsets = set()
        group_start = group * repetition
        for position in selected_positions:
            if group_start <= position < group_start + repetition:
                used_offsets.add(position - group_start)

        available_offsets = [
            offset for offset in range(repetition) if offset not in used_offsets
        ]
        offset = int(rng.choice(available_offsets))
        selected_positions.append(group_start + offset)
        group_counts[group] += 1

    return stable_indices[np.array(selected_positions, dtype=np.int64)]


def _random_noise_success_rate(
    fe: FuzzyExtractor,
    golden: np.ndarray,
    helper_data: dict,
    expected_key: bytes,
    ber_test: float,
    trials: int,
    rng: np.random.Generator,
) -> float:
    if trials <= 0:
        raise ValueError("random_noise_trials must be positive")

    indices = np.array(helper_data["stable_indices"])
    clean_selected = golden[indices]
    successes = 0

    for _ in range(trials):
        flips = rng.random(len(clean_selected)) < ber_test
        noisy_selected = clean_selected ^ flips.astype(np.uint8)
        if fe._rep_from_selected_bits(noisy_selected, helper_data) == expected_key:
            successes += 1

    return successes / trials


if __name__ == "__main__":
    simulate_all(
        masks_path=Path("artifacts/masks.json"),
        stability_csv_path=Path("artifacts/stability_summary.csv"),
        output_path=Path("artifacts/fuzzy_extractor_results.csv"),
        threshold=0.9,
        bits_needed=256,
        repetition=11,
        ber_test=0.05,
        experiment_seed=20260506,
        random_noise_trials=100,
    )
