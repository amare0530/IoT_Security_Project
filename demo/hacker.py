"""Interactive attacker terminal for the live demo.

Run:  python -m demo.hacker            (add --broker <IP> from a second laptop)

This client has no key and no helper data. It can only do what any MQTT
subscriber can: read packets on the broker and publish its own.
"""

from __future__ import annotations

import argparse
import json
import secrets
import sys
import threading
import time
from pathlib import Path

import paho.mqtt.client as mqtt

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from demo import ui

CONTROL_TOPIC = "iot/auth/demo/control"
WEAK_LOGIN_TOPIC = "iot/weak/login"
WEAK_RESULT_TOPIC = "iot/weak/result"
FIELDS = ("uid", "nonce", "timestamp", "hmac")
MENU = (
    "1=重放側錄到的封包    2=自己改封包再送\n"
    "3=連續亂猜 1000 次    4=破解對照組密碼\n"
    "直接打任何字=當成密碼送出    q=結束"
)


def build_packet(challenge: dict, hmac_value: str) -> dict[str, str]:
    return {
        "uid": str(challenge.get("uid", "")),
        "nonce": str(challenge.get("nonce", "")),
        "timestamp": str(challenge.get("timestamp", "")),
        "hmac": hmac_value,
    }


def edit_packet(packet: dict[str, str], field: str, value: str) -> dict[str, str]:
    if field not in FIELDS:
        raise ValueError(f"unknown field: {field}")
    changed = dict(packet)
    changed[field] = value or secrets.token_hex(16 if field != "hmac" else 32)
    return changed


def random_tag() -> str:
    return secrets.token_hex(32)


class Hacker:
    def __init__(self, args: argparse.Namespace):
        self.args = args
        self.last_challenge: dict | None = None
        self.captured: dict | None = None
        self.own_packets: set[str] = set()
        self.results = {"ACCEPT": 0, "REJECT": 0}
        self.attacks = 0
        self.wins = 0
        self.quiet = False
        self.challenge_seen = threading.Event()
        self.weak_hit = threading.Event()
        self.weak_pin: str | None = None
        self.weak_replies = 0
        self.client = mqtt.Client(
            mqtt.CallbackAPIVersion.VERSION2,
            client_id=f"puf-demo-hacker-{secrets.token_hex(3)}",
        )
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message

    # -- sniffing ------------------------------------------------------------
    def on_connect(self, client, userdata, flags, reason_code, properties):
        for topic in (self.args.challenge_topic, self.args.response_topic,
                      self.args.result_topic):
            client.subscribe(topic, qos=1)
        client.subscribe(WEAK_RESULT_TOPIC, qos=0)

    def on_message(self, client, userdata, message):
        raw = message.payload.decode("utf-8", errors="replace")
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            return
        if not isinstance(payload, dict):
            return
        if message.topic == WEAK_RESULT_TOPIC:
            self.weak_replies += 1
            if payload.get("status") == "ACCEPT":
                self.weak_pin = str(payload.get("pin"))
                self.weak_hit.set()
            return
        if message.topic == self.args.result_topic:
            status = payload.get("status")
            if status in self.results:
                self.results[status] += 1
            if not self.quiet:
                ui.say(f"  [側錄] result     {status}", "dim")
            return
        if message.topic == self.args.challenge_topic:
            self.last_challenge = payload
            self.challenge_seen.set()
            if not self.quiet:
                ui.say(f"  [側錄] challenge  nonce={ui.short(payload.get('nonce'), 8)}", "dim")
            return
        if raw in self.own_packets:
            return
        self.captured = payload
        if not self.quiet:
            ui.say("  [側錄] response", "yellow")
            for field in FIELDS:
                ui.say(f"         {field:<9} {ui.short(payload.get(field), 10)}", "yellow")
            ui.say("         只有這四個欄位，沒有金鑰", "dim")

    # -- sending -------------------------------------------------------------
    def send(self, packet: dict) -> None:
        raw = json.dumps(packet)
        self.own_packets.add(raw)
        self.client.publish(self.args.response_topic, raw, qos=1)

    def fresh_challenge(self) -> dict | None:
        self.challenge_seen.clear()
        self.client.publish(CONTROL_TOPIC, json.dumps({"cmd": "challenge"}), qos=1)
        if not self.challenge_seen.wait(timeout=self.args.timeout):
            ui.say("  等不到 challenge，確認 server 是否已啟動", "red")
            return None
        return self.last_challenge

    def attack(self, packets: list[dict], label: str, wait: float = 2.5) -> None:
        before = dict(self.results)
        for packet in packets:
            self.send(packet)
        deadline = time.monotonic() + wait
        expected = len(packets)
        while time.monotonic() < deadline:
            got = sum(self.results.values()) - sum(before.values())
            if got >= expected:
                break
            time.sleep(0.05)
        accepted = self.results["ACCEPT"] - before["ACCEPT"]
        rejected = self.results["REJECT"] - before["REJECT"]
        silent = expected - accepted - rejected
        self.attacks += expected
        self.wins += accepted
        if accepted:
            ui.banner(f"{label}：成功 {accepted} 次", True)
        else:
            ui.banner(f"{label}：被拒絕 {rejected:,} 次", False)
            if silent > 0:
                ui.say(f"  另有 {silent:,} 個封包 Server 直接丟棄、沒有回覆", "dim")
        ui.say(f"  累計攻擊 {self.attacks:,} 次，成功 {self.wins} 次", "bold")

    # -- commands ------------------------------------------------------------
    def replay(self) -> None:
        if self.captured is None:
            ui.say("  還沒側錄到封包，先讓 Device 認證一次", "red")
            return
        ui.say("  把剛才側錄到的封包原封不動再送一次", "cyan")
        self.attack([self.captured], "重放")

    def guess(self, value: str) -> None:
        challenge = self.fresh_challenge()
        if challenge is None:
            return
        ui.say(f"  用「{ui.short(value, 12)}」當作 hmac 送出", "cyan")
        self.attack([build_packet(challenge, value)], "猜密碼")

    def craft(self) -> None:
        challenge = self.fresh_challenge()
        if challenge is None:
            return
        stolen = self.captured.get("hmac", "") if self.captured else random_tag()
        packet = build_packet(challenge, str(stolen))
        ui.say("  拿側錄到的舊 hmac 回答新的 challenge：", "cyan")
        for field in FIELDS:
            ui.say(f"    {field:<9} {ui.short(packet[field], 14)}")
        ui.say("  要改哪一欄？uid / nonce / timestamp / hmac")
        field = input("  （直接 Enter 不改）> ").strip().lower()
        if field:
            if field not in FIELDS:
                ui.say("  沒有這個欄位", "red")
                return
            value = input("  新的值（Enter=隨機）> ").strip()
            packet = edit_packet(packet, field, value)
        self.attack([packet], "偽造封包")

    def flood(self, count: int) -> None:
        challenge = self.fresh_challenge()
        if challenge is None:
            return
        ui.say(f"  連續亂猜 {count:,} 個 hmac", "cyan")
        ui.say("  （可能的 tag 有 2^256 種）", "dim")
        self.quiet = True
        try:
            self.attack(
                [build_packet(challenge, random_tag()) for _ in range(count)],
                "暴力亂猜",
                wait=max(self.args.timeout, 10),
            )
        finally:
            self.quiet = False

    def crack_weak_pin(self) -> None:
        ui.say("  對照組：只靠 4 位數密碼，沒有 PUF", "cyan")
        self.weak_hit.clear()
        self.weak_pin = None
        self.weak_replies = 0
        tried = 0
        for number in range(10000):
            if self.weak_hit.is_set():
                break
            pin = f"{number:04d}"
            self.client.publish(WEAK_LOGIN_TOPIC, json.dumps({"pin": pin}), qos=0)
            tried += 1
            if number % 41 == 0:
                ui.say(f"\r  嘗試中 {pin}  已送出 {tried:,} ", "yellow", end="")
                ui.pause(0.012)
        self.weak_hit.wait(timeout=self.args.timeout)
        ui.say()
        if self.weak_pin is None:
            ui.say("  沒有收到對照組的回應，檢查 server", "red")
        else:
            ui.banner(f"密碼是 {self.weak_pin}，冒充成功", True)
            ui.say("  4 位數只有 10,000 種，幾秒就試完", "dim")

    def handle(self, line: str) -> bool:
        text = line.strip()
        if text == "q":
            return False
        if text == "":
            ui.say(MENU, "dim")
        elif text == "1":
            self.replay()
        elif text == "2":
            self.craft()
        elif text == "3":
            self.flood(self.args.flood)
        elif text == "4":
            self.crack_weak_pin()
        else:
            self.guess(text)
        return True

    def run(self) -> None:
        ui.rule("HACKER  沒有金鑰，只能側錄與發送封包")
        self.client.connect(self.args.broker, self.args.port, keepalive=60)
        self.client.loop_start()
        ui.say(f"  已連上 broker {self.args.broker}:{self.args.port}，開始側錄", "dim")
        try:
            while True:
                ui.say(f"\n{MENU}", "dim")
                try:
                    line = input("Hacker> ")
                except EOFError:
                    break
                if not self.handle(line):
                    break
        except KeyboardInterrupt:
            pass
        finally:
            self.client.loop_stop()
            self.client.disconnect()


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Interactive attacker for the live demo")
    parser.add_argument("--broker", default="localhost")
    parser.add_argument("--port", type=int, default=1883)
    parser.add_argument("--challenge-topic", default="iot/auth/challenge")
    parser.add_argument("--response-topic", default="iot/auth/response")
    parser.add_argument("--result-topic", default="iot/auth/result")
    parser.add_argument("--flood", type=int, default=1000)
    parser.add_argument("--timeout", type=float, default=6)
    parser.add_argument("--fast", action="store_true", help="no animation delays")
    return parser.parse_args(argv)


def main() -> None:
    args = parse_args()
    ui.setup(fast=args.fast)
    try:
        Hacker(args).run()
    except OSError as exc:
        ui.say(f"無法連上 broker：{exc}", "red")
        sys.exit(1)


if __name__ == "__main__":
    main()
