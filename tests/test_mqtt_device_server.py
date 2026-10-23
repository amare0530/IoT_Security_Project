import json
from pathlib import Path

import numpy as np

from mqtt.device import DeviceConfig, run_device
from mqtt.server import ServerConfig, run_server
from puf.fuzzy_extractor import FuzzyExtractor


class Message:
    def __init__(self, topic: str, payload: dict):
        self.topic = topic
        self.payload = json.dumps(payload).encode()


class DeviceClient:
    def __init__(self, *args, **kwargs):
        self.on_connect = None
        self.on_message = None
        self.published = []

    def subscribe(self, *args, **kwargs):
        pass

    def publish(self, topic, payload, **kwargs):
        self.published.append((topic, json.loads(payload)))

    def connect(self, *args, **kwargs):
        self.on_connect(self, None, None, None, None)

    def loop_forever(self):
        challenge = {"uid": "device-001", "nonce": "n1", "timestamp": "1"}
        self.on_message(self, None, Message("iot/auth/challenge", challenge))
        challenge["nonce"] = "n2"
        self.on_message(self, None, Message("iot/auth/challenge", challenge))


def _write_bundle(root: Path) -> None:
    golden = np.random.default_rng(5).integers(0, 2, 655360, dtype=np.uint8)
    mask = np.zeros(655360, dtype=np.uint8)
    mask[:2816] = 1
    extractor = FuzzyExtractor()
    key, helper = extractor.gen(golden, mask, "device-001", np.random.default_rng(6))
    (root / "response.json").write_text(
        json.dumps({"device-001": {"response_bits": golden.tolist()}})
    )
    (root / "helper.json").write_text(json.dumps({"device-001": helper}))
    return key


def test_device_rebuilds_for_each_challenge_and_best_effort_clears_buffer(
    monkeypatch, tmp_path, capsys
):
    key = _write_bundle(tmp_path)
    clients = []
    calls = []
    original_resolve = __import__(
        "mqtt.device", fromlist=["resolve_reconstructed_key"]
    ).resolve_reconstructed_key

    def counted_resolve(*args, **kwargs):
        calls.append(True)
        return original_resolve(*args, **kwargs)

    monkeypatch.setattr("mqtt.device.resolve_reconstructed_key", counted_resolve)
    monkeypatch.setattr("mqtt.device.mqtt.Client", lambda *a, **k: clients.append(DeviceClient()) or clients[-1])

    run_device(
        DeviceConfig(
            response_registry=tmp_path / "response.json",
            helper_registry=tmp_path / "helper.json",
        )
    )

    client = clients[0]
    responses = [payload for topic, payload in client.published if topic.endswith("/response")]
    assert len(responses) == 2
    assert len(calls) == 2
    assert all(set(payload) == {"uid", "nonce", "timestamp", "hmac"} for payload in responses)
    assert "best-effort cleared" in capsys.readouterr().out


def test_server_accepts_and_publishes_unreasoned_result(monkeypatch, tmp_path):
    key = bytes.fromhex("00112233445566778899aabbccddeeff")
    registry = tmp_path / "keys.csv"
    registry.write_text("uid,key_hex\ndevice-001," + key.hex() + "\n")

    class ServerClient:
        def __init__(self, *args, **kwargs):
            self.on_connect = None
            self.on_message = None
            self.published = []
            self.connected = True

        def subscribe(self, *args, **kwargs):
            pass

        def publish(self, topic, payload, **kwargs):
            value = json.loads(payload)
            self.published.append((topic, value))
            if topic.endswith("/challenge"):
                from auth.hmac_auth import PUFAuthenticator

                auth = PUFAuthenticator()
                response = {
                    **value,
                    "hmac": auth.generate_response(key, value["uid"], value),
                }
                self.on_message(self, None, Message("iot/auth/response", response))
                raise KeyboardInterrupt

        def connect(self, *args, **kwargs):
            self.on_connect(self, None, None, None, None)

        def loop_start(self):
            pass

        def is_connected(self):
            return self.connected

        def loop_stop(self):
            pass

        def disconnect(self):
            pass

    client = ServerClient()
    monkeypatch.setattr("mqtt.server.mqtt.Client", lambda *a, **k: client)
    config = ServerConfig(
        key_registry=registry,
        challenge_interval_seconds=0,
    )
    run_server(config)
    results = [payload for topic, payload in client.published if topic.endswith("/result")]
    assert results and results[-1] == {"uid": "device-001", "status": "ACCEPT"}
    assert "reason" not in results[-1]


def test_device_rep_failure_does_not_publish(monkeypatch, tmp_path):
    _write_bundle(tmp_path)
    clients = []
    monkeypatch.setattr(
        "mqtt.device.resolve_reconstructed_key",
        lambda *args, **kwargs: (_ for _ in ()).throw(ValueError("bad helper")),
    )
    monkeypatch.setattr(
        "mqtt.device.mqtt.Client",
        lambda *a, **k: clients.append(DeviceClient()) or clients[-1],
    )
    run_device(
        DeviceConfig(
            response_registry=tmp_path / "response.json",
            helper_registry=tmp_path / "helper.json",
        )
    )
    assert not [topic for topic, _ in clients[0].published if topic.endswith("/response")]
