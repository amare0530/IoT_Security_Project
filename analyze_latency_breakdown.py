"""
Latency breakdown benchmark for the thesis report.

Measures four components:
1) Network round-trip via MQTT loopback publish/receive.
2) HMAC challenge derivation.
3) Database query on crp_records.
4) Hamming distance comparison.

Outputs:
- artifacts/latency_breakdown.json
- artifacts/latency_breakdown.csv
- artifacts/latency_breakdown.png
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import hmac
import json
import random
import sqlite3
import statistics
import threading
import time
import uuid
from pathlib import Path

import paho.mqtt.client as mqtt

from config import MQTT_CONFIG, VRF_CONFIG


ARTIFACTS_DIR = Path("artifacts")
JSON_OUT = ARTIFACTS_DIR / "latency_breakdown.json"
CSV_OUT = ARTIFACTS_DIR / "latency_breakdown.csv"
PNG_OUT = ARTIFACTS_DIR / "latency_breakdown.png"
DB_PATH = "authentication_history.db"


def _summary_stats(values_ms: list[float]) -> dict:
    if not values_ms:
        return {
            "count": 0,
            "mean_ms": None,
            "median_ms": None,
            "p95_ms": None,
            "min_ms": None,
            "max_ms": None,
            "std_ms": None,
        }

    sorted_vals = sorted(values_ms)
    p95_idx = min(len(sorted_vals) - 1, max(0, int(round(0.95 * (len(sorted_vals) - 1)))))
    return {
        "count": len(values_ms),
        "mean_ms": statistics.mean(values_ms),
        "median_ms": statistics.median(values_ms),
        "p95_ms": sorted_vals[p95_idx],
        "min_ms": min(values_ms),
        "max_ms": max(values_ms),
        "std_ms": statistics.pstdev(values_ms) if len(values_ms) > 1 else 0.0,
    }


def benchmark_hmac(samples: int) -> list[float]:
    key = VRF_CONFIG["server_secret_key"].encode("utf-8")
    durations: list[float] = []
    for i in range(samples):
        seed = f"latency_seed_{i}_{random.randint(0, 10**9)}".encode("utf-8")
        t0 = time.perf_counter()
        hmac.new(key, seed, hashlib.sha256).hexdigest()
        t1 = time.perf_counter()
        durations.append((t1 - t0) * 1000.0)
    return durations


def benchmark_db_query(samples: int) -> list[float]:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    # Keep query simple and aligned with dataset-first retrieval path.
    query = """
        SELECT challenge, response
        FROM crp_records
        WHERE source='real'
        ORDER BY RANDOM()
        LIMIT 1
    """
    durations: list[float] = []
    for _ in range(samples):
        t0 = time.perf_counter()
        row = cur.execute(query).fetchone()
        t1 = time.perf_counter()
        if row is None:
            conn.close()
            raise RuntimeError("crp_records has no rows with source='real'")
        durations.append((t1 - t0) * 1000.0)
    conn.close()
    return durations


def _hamming_distance_hex(hex_a: str, hex_b: str) -> int:
    a = int(hex_a, 16)
    b = int(hex_b, 16)
    return (a ^ b).bit_count()


def benchmark_hd_compare(samples: int) -> list[float]:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    rows = cur.execute(
        """
        SELECT challenge, response
        FROM crp_records
        WHERE source='real'
        LIMIT 2000
        """
    ).fetchall()
    conn.close()

    if not rows:
        raise RuntimeError("crp_records has no usable rows for HD benchmark")

    durations: list[float] = []
    for _ in range(samples):
        challenge, response = random.choice(rows)
        # Compare response to challenge only for timing consistency.
        t0 = time.perf_counter()
        _hamming_distance_hex(response, challenge)
        t1 = time.perf_counter()
        durations.append((t1 - t0) * 1000.0)
    return durations


def benchmark_network_mqtt(samples: int, timeout_s: float) -> list[float]:
    broker = MQTT_CONFIG["broker_host"]
    port = int(MQTT_CONFIG["broker_port"])
    topic = f"fujen/iot/latency/{uuid.uuid4().hex}"
    client_id = f"latency_probe_{uuid.uuid4().hex[:8]}"

    durations: list[float] = []
    lock = threading.Lock()
    pending_send_times: dict[str, float] = {}
    pending_events: dict[str, threading.Event] = {}

    def on_connect(client, userdata, flags, rc):
        if rc != 0:
            raise RuntimeError(f"MQTT connect failed, rc={rc}")
        client.subscribe(topic, qos=1)

    def on_message(client, userdata, msg):
        payload = msg.payload.decode("utf-8", errors="ignore")
        recv_t = time.perf_counter()
        with lock:
            send_t = pending_send_times.get(payload)
            evt = pending_events.get(payload)
        if send_t is not None and evt is not None:
            durations.append((recv_t - send_t) * 1000.0)
            evt.set()

    client = mqtt.Client(client_id=client_id, clean_session=True)
    client.on_connect = on_connect
    client.on_message = on_message

    client.connect(broker, port, MQTT_CONFIG.get("keepalive", 60))
    client.loop_start()

    try:
        # Give subscribe path a short warm-up period.
        time.sleep(0.8)
        for i in range(samples):
            token = f"{i}_{uuid.uuid4().hex}"
            evt = threading.Event()
            with lock:
                pending_events[token] = evt
                pending_send_times[token] = time.perf_counter()
            info = client.publish(topic, payload=token, qos=1)
            info.wait_for_publish(timeout=timeout_s)
            ok = evt.wait(timeout=timeout_s)
            with lock:
                pending_events.pop(token, None)
                pending_send_times.pop(token, None)
            if not ok:
                raise TimeoutError(f"MQTT loopback timeout on sample {i + 1}/{samples}")
    finally:
        client.loop_stop()
        client.disconnect()

    return durations


def save_outputs(raw: dict[str, list[float]], summary: dict[str, dict]) -> None:
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

    with JSON_OUT.open("w", encoding="utf-8") as f:
        json.dump(
            {
                "components_ms": raw,
                "summary": summary,
                "chart": str(PNG_OUT),
            },
            f,
            ensure_ascii=False,
            indent=2,
        )

    with CSV_OUT.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["component", "count", "mean_ms", "median_ms", "p95_ms", "min_ms", "max_ms", "std_ms"],
        )
        writer.writeheader()
        for component, stats in summary.items():
            writer.writerow({"component": component, **stats})


def save_chart(summary: dict[str, dict]) -> None:
    import matplotlib.pyplot as plt

    labels = ["Network RTT", "HMAC", "DB Query", "HD Compare"]
    keys = ["network_rtt", "hmac_compute", "db_query", "hd_compare"]
    means = [summary[k]["mean_ms"] for k in keys]
    p95s = [summary[k]["p95_ms"] for k in keys]

    fig, ax = plt.subplots(figsize=(8.5, 5.2))
    bars = ax.bar(labels, means, color=["#2a9d8f", "#e9c46a", "#f4a261", "#e76f51"], alpha=0.9)
    ax.scatter(labels, p95s, color="#264653", marker="D", s=42, label="p95")

    for bar, mean in zip(bars, means):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height(), f"{mean:.3f}", ha="center", va="bottom", fontsize=9)

    ax.set_ylabel("Latency (ms)")
    ax.set_title("Authentication Latency Breakdown")
    ax.grid(axis="y", alpha=0.25)
    ax.legend()
    plt.tight_layout()
    plt.savefig(PNG_OUT, dpi=220)
    plt.close(fig)


def main() -> int:
    parser = argparse.ArgumentParser(description="Benchmark latency breakdown for advisor chart")
    parser.add_argument("--samples", type=int, default=120, help="Samples per component")
    parser.add_argument("--mqtt-timeout", type=float, default=5.0, help="Timeout in seconds for each MQTT loopback sample")
    args = parser.parse_args()

    random.seed(20260409)

    print("[1/4] Measuring Network RTT via MQTT loopback...")
    network_rtt = benchmark_network_mqtt(args.samples, args.mqtt_timeout)

    print("[2/4] Measuring HMAC compute latency...")
    hmac_compute = benchmark_hmac(args.samples)

    print("[3/4] Measuring DB query latency...")
    db_query = benchmark_db_query(args.samples)

    print("[4/4] Measuring HD compare latency...")
    hd_compare = benchmark_hd_compare(args.samples)

    raw = {
        "network_rtt": network_rtt,
        "hmac_compute": hmac_compute,
        "db_query": db_query,
        "hd_compare": hd_compare,
    }
    summary = {k: _summary_stats(v) for k, v in raw.items()}

    save_outputs(raw, summary)
    save_chart(summary)

    print("\nLatency breakdown summary (mean ms / p95 ms):")
    for key in ["network_rtt", "hmac_compute", "db_query", "hd_compare"]:
        print(f"- {key}: {summary[key]['mean_ms']:.3f} / {summary[key]['p95_ms']:.3f}")

    print(f"\nSaved: {JSON_OUT}")
    print(f"Saved: {CSV_OUT}")
    print(f"Saved: {PNG_OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())