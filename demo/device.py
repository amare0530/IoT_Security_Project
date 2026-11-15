"""Demo shell around the real device steps.

Run:  python -m demo.device

Press Enter to "power on" and authenticate. The key is rebuilt for every
challenge with FuzzyExtractor.rep and the response is built with
mqtt.device.build_response_payload, as in mqtt/device.py. This file adds the
vote display, an artificial noise control and a wrong-chip control.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import threading
from pathlib import Path

import numpy as np
import paho.mqtt.client as mqtt

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from auth.hmac_auth import PUFAuthenticator
from demo import ui
from mqtt.device import build_response_payload
from puf.fuzzy_extractor import FuzzyExtractor
from puf.key_provider import load_reconstruction_inputs

CONTROL_TOPIC = "iot/auth/demo/control"
HELP = "Enter=開機認證   n 5=加 5% 雜訊後認證   x=換成別顆晶片   q=結束"


def only_uid_in_helper(path: Path) -> str:
    with path.open(encoding="utf-8") as handle:
        payload = json.load(handle)
    uids = [key for key, value in payload.items() if isinstance(value, dict)]
    if len(uids) != 1:
        raise ValueError(f"{path} has {len(uids)} uids; pass --uid")
    return uids[0]


def load_other_chip(path: Path) -> np.ndarray:
    """First SRAM reading in a response.json that belongs to another device."""
    with path.open(encoding="utf-8") as handle:
        payload = json.load(handle)
    record = next(iter(payload.values()))
    bits = record.get("response_bits") if isinstance(record, dict) else record
    return np.asarray(bits, dtype=np.uint8)


def add_noise(
    response_bits: np.ndarray,
    stable_indices: np.ndarray,
    bit_error_rate: float,
    rng: np.random.Generator,
) -> tuple[np.ndarray, int]:
    """Artificially flip a share of the bits Rep() will read. Returns a copy."""
    noisy = response_bits.copy()
    flips = stable_indices[rng.random(len(stable_indices)) < bit_error_rate]
    noisy[flips] ^= 1
    return noisy, int(len(flips))


def vote_tally(response_bits: np.ndarray, helper: dict) -> np.ndarray:
    """Votes for 1 in each repetition group (the input to Rep's majority vote)."""
    indices = np.asarray(helper["stable_indices"], dtype=np.int64)
    encoded = np.asarray(helper["W"], dtype=np.uint8)
    groups = (encoded ^ response_bits[indices]).reshape(
        helper["bits_needed"], helper["repetition"]
    )
    return groups.sum(axis=1)


def dissent(votes: np.ndarray, repetition: int) -> np.ndarray:
    """Votes that lost in each group: 0 means unanimous."""
    return np.minimum(votes, repetition - votes)


def show_votes(votes: np.ndarray, repetition: int) -> None:
    losing = dissent(votes, repetition)
    row = 64
    for start in range(0, len(losing), row):
        line = []
        for value in losing[start : start + row]:
            if value == 0:
                line.append(ui.paint("█", "green"))
            elif value <= 2:
                line.append(ui.paint("█", "yellow"))
            else:
                line.append(ui.paint("█", "red"))
        ui.say("  " + "".join(line))
        ui.pause(0.25)
    ui.say(
        f"  {ui.paint('█', 'green')} {int((losing == 0).sum())} 組全票一致   "
        f"{ui.paint('█', 'yellow')} {int(((losing > 0) & (losing <= 2)).sum())} 組有雜訊、多數決救回   "
        f"{ui.paint('█', 'red')} {int((losing > 2).sum())} 組票數接近"
    )


class DemoDevice:
    def __init__(self, args: argparse.Namespace):
        self.args = args
        self.uid = args.uid or only_uid_in_helper(args.helper_registry)
        self.authenticator = PUFAuthenticator()
        self.rng = np.random.default_rng()
        self.armed: dict | None = None
        self.last_nonce: str | None = None
        self.done = threading.Event()
        self.client = mqtt.Client(
            mqtt.CallbackAPIVersion.VERSION2, client_id=f"puf-demo-device-{self.uid}"
        )
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message

    def on_connect(self, client, userdata, flags, reason_code, properties):
        client.subscribe(self.args.challenge_topic, qos=1)
        client.subscribe(self.args.result_topic, qos=1)

    def on_message(self, client, userdata, message):
        try:
            payload = json.loads(message.payload.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return
        if not isinstance(payload, dict) or payload.get("uid") != self.uid:
            return
        if message.topic == self.args.result_topic:
            if self.last_nonce and payload.get("nonce") == self.last_nonce:
                self.last_nonce = None
                status = payload.get("status")
                ui.banner(f"Server 回覆：{status}", status == "ACCEPT")
                self.done.set()
            return
        if self.armed is None or "nonce" not in payload or "timestamp" not in payload:
            return
        mode, self.armed = self.armed, None
        self.respond({"nonce": payload["nonce"], "timestamp": payload["timestamp"]}, mode)

    def respond(self, challenge: dict[str, str], mode: dict) -> None:
        ui.say(f"← 收到 challenge  nonce={ui.short(challenge['nonce'], 8)}", "cyan")
        key_buffer: bytearray | None = None
        try:
            ui.say(f"  讀取 helper data   {self.args.helper_registry}")
            ui.say(f"  讀取 SRAM 開機值   {self.args.response_registry}")
            bits, helper = load_reconstruction_inputs(
                self.uid, self.args.response_registry, self.args.helper_registry
            )
            indices = np.asarray(helper["stable_indices"], dtype=np.int64)
            ui.say(f"  SRAM {len(bits):,} 位元，取用 {len(indices):,} 個穩定位元 "
                   f"= {helper['bits_needed']} 個金鑰位元 × {helper['repetition']} 票")
            if mode["chip"] == "other":
                bits = load_other_chip(self.args.other_chip)
                ui.say(f"  ！改用別顆晶片的 SRAM 開機值  {self.args.other_chip}", "yellow", "bold")
            if mode["noise"] > 0:
                bits, flipped = add_noise(bits, indices, mode["noise"], self.rng)
                ui.say(f"  ！人工翻轉 {flipped} / {len(indices)} 個位元"
                       f"（{mode['noise']:.0%} 雜訊）", "yellow", "bold")
            ui.say("  Rep()：每個金鑰位元 11 票多數決  (puf/fuzzy_extractor.py  rep)")
            show_votes(vote_tally(bits, helper), helper["repetition"])
            extractor = FuzzyExtractor(
                bits_needed=helper["bits_needed"], repetition=helper["repetition"]
            )
            key_buffer = bytearray(extractor.rep(bits, helper))
            ui.say(f"  重建金鑰指紋    {hashlib.sha256(bytes(key_buffer)).hexdigest()[:8]}"
                   "（與 Server 那邊的指紋比對）")
            response = build_response_payload(
                self.authenticator, bytes(key_buffer), self.uid, challenge
            )
            self.last_nonce = challenge["nonce"]
            self.client.publish(self.args.response_topic, json.dumps(response), qos=1)
            ui.say(f"→ 送出 response   hmac={ui.short(response['hmac'], 10)}", "cyan")
        except Exception as exc:  # shown on screen; the device keeps running
            ui.say(f"  金鑰重建失敗，未送出回應：{exc}", "red")
            self.done.set()
        finally:
            if key_buffer is not None:
                for index in range(len(key_buffer)):
                    key_buffer[index] = 0
                ui.say("  金鑰已從記憶體清除（Python 只能盡力而為）", "dim")

    def boot(self, noise: float = 0.0, chip: str = "own") -> None:
        ui.rule("開機，向 Server 請求認證")
        self.done.clear()
        self.armed = {"noise": noise, "chip": chip}
        self.client.publish(CONTROL_TOPIC, json.dumps({"cmd": "challenge"}), qos=1)
        if not self.done.wait(timeout=self.args.timeout):
            self.armed = None
            ui.say("  等不到 Server 回應，確認 broker 與 server 是否已啟動", "red")

    def handle(self, line: str) -> bool:
        """Run one typed command. Returns False to quit."""
        parts = line.strip().lower().split()
        if not parts:
            self.boot()
        elif parts[0] == "q":
            return False
        elif parts[0] == "n":
            try:
                percent = float(parts[1]) if len(parts) > 1 else 5.0
            except ValueError:
                percent = -1
            if not 0 <= percent <= 50:
                ui.say("  雜訊請輸入 0 到 50 之間的數字，例如 n 5", "red")
            else:
                self.boot(noise=percent / 100)
        elif parts[0] == "x":
            if self.args.other_chip is None or not self.args.other_chip.exists():
                ui.say("  沒有別顆晶片的資料，請用 --other-chip 指定檔案", "red")
            else:
                self.boot(chip="other")
        else:
            ui.say(f"  {HELP}", "dim")
        return True

    def run(self) -> None:
        ui.rule("DEVICE  (金鑰重建：puf/fuzzy_extractor.py  rep)")
        ui.say(f"  設備 UID   {self.uid}")
        ui.say("  本機只有 helper data 與 SRAM 開機值，沒有存金鑰")
        self.client.connect(self.args.broker, self.args.port, keepalive=60)
        self.client.loop_start()
        try:
            while True:
                ui.say(f"\n{HELP}", "dim")
                try:
                    line = input("Device> ")
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
    parser = argparse.ArgumentParser(description="PUF MQTT demo device (presentation shell)")
    parser.add_argument("--broker", default="localhost")
    parser.add_argument("--port", type=int, default=1883)
    parser.add_argument("--uid", default=None, help="default: the only uid in helper data")
    parser.add_argument("--response-registry", type=Path,
                        default=Path("demo_bundle/device/response.json"))
    parser.add_argument("--helper-registry", type=Path,
                        default=Path("demo_bundle/device/helper_data.json"))
    parser.add_argument("--other-chip", type=Path,
                        default=Path("demo_bundle/attacker/response.json"),
                        help="response.json of a different device, for the wrong-chip step")
    parser.add_argument("--challenge-topic", default="iot/auth/challenge")
    parser.add_argument("--response-topic", default="iot/auth/response")
    parser.add_argument("--result-topic", default="iot/auth/result")
    parser.add_argument("--timeout", type=float, default=8)
    parser.add_argument("--fast", action="store_true", help="no animation delays")
    return parser.parse_args(argv)


def main() -> None:
    args = parse_args()
    ui.setup(fast=args.fast)
    try:
        DemoDevice(args).run()
    except (FileNotFoundError, KeyError, ValueError, OSError) as exc:
        ui.say(f"無法啟動 device：{exc}", "red")
        sys.exit(1)


if __name__ == "__main__":
    main()
