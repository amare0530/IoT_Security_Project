"""Demo shell around the real server checks.

Run:  python -m demo.server

The accept/reject decision is made by mqtt.server.classify_response and
PUFAuthenticator.verify_response, exactly as in mqtt/server.py. This file
only adds: repeatable challenges on request, a gate-by-gate display, and an
intentionally weak 4-digit-PIN login used as a contrast case.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import inspect
import json
import secrets
import sys
import threading
import time
from pathlib import Path

import paho.mqtt.client as mqtt

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from auth.hmac_auth import PUFAuthenticator
from demo import ui
from mqtt.server import build_challenge_payload, classify_response, extract_challenge
from puf.key_provider import DEFAULT_KEY_REGISTRY, resolve_key_bytes

CONTROL_TOPIC = "iot/auth/demo/control"
WEAK_LOGIN_TOPIC = "iot/weak/login"
WEAK_RESULT_TOPIC = "iot/weak/result"
BUNDLE_REGISTRY = Path("demo_bundle/server/key_registry.csv")

# Order follows classify_response in mqtt/server.py.
GATES: list[tuple[str, tuple[str, ...]]] = [
    ("封包格式正確", ("invalid challenge payload",)),
    ("UID 相符", ("uid mismatch",)),
    ("nonce 沒用過", ("replay: nonce already used",)),
    ("與發出的 challenge 一致", ("missing pending challenge", "challenge mismatch")),
    ("timestamp 在視窗內", ("invalid timestamp", "timestamp future", "timestamp expired")),
    ("HMAC tag 相符", ("tag mismatch",)),
]


def gate_index(reason: str | None) -> int | None:
    """Return the 0-based gate that rejected, or None when all gates pass."""
    if reason is None:
        return None
    for index, (_, reasons) in enumerate(GATES):
        if reason in reasons:
            return index
    return len(GATES) - 1


def source_line(reason: str) -> str:
    """Clickable file:line of the check in mqtt/server.py that produced reason."""
    lines, start = inspect.getsourcelines(classify_response)
    for offset, line in enumerate(lines):
        if f'"{reason}"' in line:
            return f"mqtt/server.py:{start + offset}"
    return f"mqtt/server.py:{start}"


def fingerprint(key: bytes) -> str:
    """Short display-only digest so two terminals can be compared by eye."""
    return hashlib.sha256(key).hexdigest()[:8]


def only_uid_in_registry(path: Path) -> str:
    with path.open(newline="", encoding="utf-8") as handle:
        uids = [row["uid"] for row in csv.DictReader(handle) if row.get("uid")]
    if len(uids) != 1:
        raise ValueError(f"{path} has {len(uids)} uids; pass --uid")
    return uids[0]


def check_pin(expected: str, attempt: object) -> bool:
    return isinstance(attempt, str) and attempt == expected


class DemoServer:
    def __init__(self, args: argparse.Namespace):
        self.args = args
        self.registry = args.key_registry
        self.uid = args.uid or only_uid_in_registry(self.registry)
        self.key = resolve_key_bytes(self.uid, None, self.registry)
        self.authenticator = PUFAuthenticator(time_window_seconds=args.time_window)
        self.pending: dict[str, dict[str, str]] = {}
        self.weak_pin = args.weak_pin or f"{secrets.randbelow(10000):04d}"
        self.weak_attempts = 0
        self.last_decision = 0.0
        self.burst = 0
        self.accepted = 0
        self.rejected = 0
        self.lock = threading.Lock()
        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="puf-demo-server")
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message

    # -- MQTT -------------------------------------------------------------
    def on_connect(self, client, userdata, flags, reason_code, properties):
        client.subscribe(self.args.response_topic, qos=1)
        client.subscribe(CONTROL_TOPIC, qos=1)
        client.subscribe(WEAK_LOGIN_TOPIC, qos=0)
        ui.say(f"已連上 broker {self.args.broker}:{self.args.port}，等待設備", "dim")

    def on_message(self, client, userdata, message):
        try:
            payload = json.loads(message.payload.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            payload = None
        if message.topic == CONTROL_TOPIC:
            self.publish_challenge()
        elif message.topic == WEAK_LOGIN_TOPIC:
            self.handle_weak_login(payload)
        else:
            self.handle_response(payload)

    def publish_challenge(self) -> None:
        payload = build_challenge_payload(self.authenticator, self.uid)
        self.pending[self.uid] = extract_challenge(payload)
        self.client.publish(self.args.challenge_topic, json.dumps(payload), qos=1)
        self.end_burst()
        ui.say(f"→ 發出 challenge  nonce={ui.short(payload['nonce'], 8)}  "
               f"timestamp={payload['timestamp']}", "cyan")

    def publish_result(self, uid: str, nonce: str, accepted: bool) -> None:
        self.client.publish(
            self.args.result_topic,
            json.dumps({"uid": uid, "nonce": nonce,
                        "status": "ACCEPT" if accepted else "REJECT"}),
            qos=1,
        )

    # -- the real protocol decision ----------------------------------------
    def handle_response(self, payload: object) -> None:
        """Same sequence as on_message in mqtt/server.py."""
        uid = payload.get("uid", "") if isinstance(payload, dict) else ""
        reason, nonce, challenge = classify_response(
            payload, self.uid, self.pending, self.authenticator, self.key
        )
        if reason is None:
            assert challenge is not None
            is_valid, _ = self.authenticator.verify_response(
                expected_key=self.key,
                uid=uid,
                challenge=challenge,
                device_response=payload.get("hmac", ""),
            )
            if is_valid:
                del self.pending[uid]
            else:
                reason = "tag mismatch"
            self.publish_result(uid, challenge["nonce"], is_valid)
        elif uid == self.uid:
            self.publish_result(uid, nonce, False)
        self.show_decision(payload, reason)

    # -- display ------------------------------------------------------------
    def show_decision(self, payload: object, reason: str | None) -> None:
        with self.lock:
            now = time.monotonic()
            in_burst = reason is not None and now - self.last_decision < 0.4
            self.last_decision = now
            if reason is None:
                self.accepted += 1
            else:
                self.rejected += 1
            if in_burst:
                self.burst += 1
                ui.say(f"\r  ✗ REJECT ×{self.burst + 1}  {reason}   ", "red", end="")
                return
            self.end_burst()
            failed = gate_index(reason)
            ui.rule("收到 response，開始檢查")
            if isinstance(payload, dict):
                for field in ("uid", "nonce", "timestamp", "hmac"):
                    ui.say(f"  {field:<9} {ui.short(payload.get(field, '(缺)'), 14)}", "dim")
            for index, (label, _) in enumerate(GATES):
                ui.pause(0.18)
                if failed is not None and index > failed:
                    ui.say(f"  ·  第 {index + 1} 關  {label}（未檢查）", "dim")
                elif failed == index:
                    ui.say(f"  ✗  第 {index + 1} 關  {label}   ← {reason}", "red", "bold")
                    ui.say(f"       程式位置 {source_line(reason)}", "dim")
                else:
                    ui.say(f"  ✓  第 {index + 1} 關  {label}", "green")
            if failed is None:
                ui.banner("ACCEPT  設備身分確認", True)
            else:
                ui.banner(f"REJECT  停在第 {failed + 1} 關", False)
            ui.say(f"  累計  通過 {self.accepted}  拒絕 {self.rejected}", "dim")

    def end_burst(self) -> None:
        if self.burst:
            self.burst = 0
            ui.say()

    # -- contrast case: no protection ----------------------------------------
    def handle_weak_login(self, payload: object) -> None:
        attempt = payload.get("pin") if isinstance(payload, dict) else None
        ok = check_pin(self.weak_pin, attempt)
        self.weak_attempts += 1
        self.client.publish(
            WEAK_RESULT_TOPIC,
            json.dumps({"pin": attempt, "status": "ACCEPT" if ok else "REJECT"}),
            qos=0,
        )
        if ok:
            ui.say()
            ui.banner(f"對照組被攻破  第 {self.weak_attempts} 次猜中", False)
            self.weak_attempts = 0
        elif self.weak_attempts % 250 == 0:
            ui.say(f"\r  對照組：已擋下 {self.weak_attempts} 次錯誤密碼 ", "yellow", end="")

    def run(self) -> None:
        ui.rule("SERVER  (判定邏輯：mqtt/server.py  classify_response)")
        ui.say(f"  讀取金鑰登錄表  {self.registry}")
        ui.say(f"  設備 UID        {self.uid}")
        ui.say(f"  登錄金鑰指紋    {fingerprint(self.key)}（只顯示指紋，金鑰不顯示）")
        ui.say(f"  時間視窗        {self.args.time_window} 秒")
        ui.say("  對照組          4 位數密碼登入已啟用（無防護，僅供對照）", "yellow")
        self.client.connect(self.args.broker, self.args.port, keepalive=60)
        self.client.loop_start()
        try:
            while True:
                time.sleep(0.5)
        except KeyboardInterrupt:
            ui.say("\nServer 結束", "dim")
        finally:
            self.client.loop_stop()
            self.client.disconnect()


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="PUF MQTT demo server (presentation shell)")
    parser.add_argument("--broker", default="localhost")
    parser.add_argument("--port", type=int, default=1883)
    parser.add_argument("--uid", default=None, help="default: the only uid in the registry")
    parser.add_argument("--key-registry", type=Path, default=None)
    parser.add_argument("--challenge-topic", default="iot/auth/challenge")
    parser.add_argument("--response-topic", default="iot/auth/response")
    parser.add_argument("--result-topic", default="iot/auth/result")
    parser.add_argument("--time-window", type=int, default=60)
    parser.add_argument("--weak-pin", default=None, help="contrast-case PIN (default random)")
    parser.add_argument("--fast", action="store_true", help="no animation delays")
    args = parser.parse_args(argv)
    if args.key_registry is None:
        args.key_registry = BUNDLE_REGISTRY if BUNDLE_REGISTRY.exists() else DEFAULT_KEY_REGISTRY
    return args


def main() -> None:
    args = parse_args()
    ui.setup(fast=args.fast)
    try:
        DemoServer(args).run()
    except (FileNotFoundError, KeyError, ValueError, OSError) as exc:
        ui.say(f"無法啟動 server：{exc}", "red")
        sys.exit(1)


if __name__ == "__main__":
    main()
