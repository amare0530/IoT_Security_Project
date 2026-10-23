import json
import sys
from pathlib import Path

import numpy as np
import pytest

from mqtt.device import DeviceConfig, run_device
from mqtt.device import build_response_payload
from mqtt.device import parse_args as parse_device_args
import mqtt.server as server_module
from mqtt.server import ServerConfig, classify_response, run_server
from puf.fuzzy_extractor import FuzzyExtractor
from puf.key_provider import resolve_reconstructed_key


class Message:
    def __init__(self, topic: str, payload: dict):
        self.topic = topic
        self.payload = json.dumps(payload).encode()


class RawMessage:
    def __init__(self, topic: str, payload: bytes):
        self.topic = topic
        self.payload = payload


def _run_server_callback_case(
    monkeypatch,
    tmp_path,
    payload_factory,
    *,
    challenge=None,
    repeat=1,
    config=None,
    trigger=True,
):
    published = []
    logs = []
    key = bytes.fromhex("00112233445566778899aabbccddeeff")
    registry = tmp_path / "keys.csv"
    registry.write_text("uid,key_hex\ndevice-001," + key.hex() + "\n")
    challenge = challenge or {"uid": "device-001", "nonce": "n", "timestamp": "1000"}
    callback = {}
    current_client = {}

    class Client:
        def __init__(self, *args, **kwargs):
            current_client["client"] = self
            self.on_connect = None
            self.on_message = None

        def subscribe(self, *args, **kwargs):
            pass

        def publish(self, topic, payload, **kwargs):
            value = json.loads(payload)
            published.append((topic, value))
            if topic.endswith("/challenge") and payload_factory is not None:
                response = payload_factory(value, key)
                if isinstance(response, RawMessage):
                    self.on_message(self, None, response)
                else:
                    message = Message("iot/auth/response", response)
                    for _ in range(repeat):
                        self.on_message(self, None, message)
                raise KeyboardInterrupt

        def connect(self, *args, **kwargs):
            self.on_connect(self, None, None, 0, None)

        def loop_start(self):
            callback["on_message"] = self.on_message

        def is_connected(self):
            if not trigger:
                raise KeyboardInterrupt
            return True

        def loop_stop(self):
            pass

        def disconnect(self):
            pass

    monkeypatch.setattr(server_module.mqtt, "Client", Client)
    monkeypatch.setattr(server_module, "build_challenge_payload", lambda auth, uid: challenge)
    monkeypatch.setattr("builtins.print", lambda *args, **kwargs: logs.append(" ".join(map(str, args))))
    server_config = config or ServerConfig(
        key_registry=registry,
        challenge_interval_seconds=0,
    )
    server_config.key_registry = registry
    run_server(server_config)
    return published, logs, callback["on_message"], current_client["client"], key, challenge


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
    assert results and results[-1]["uid"] == "device-001"
    assert results[-1]["status"] == "ACCEPT"
    assert set(results[-1]) == {"uid", "nonce", "status"}
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


def test_device_response_delay_is_applied_for_expiry_demo(monkeypatch, tmp_path):
    _write_bundle(tmp_path)
    clients = []
    delays = []
    monkeypatch.setattr("mqtt.device.time.sleep", delays.append)
    monkeypatch.setattr(
        "mqtt.device.mqtt.Client",
        lambda *a, **k: clients.append(DeviceClient()) or clients[-1],
    )

    run_device(
        DeviceConfig(
            response_registry=tmp_path / "response.json",
            helper_registry=tmp_path / "helper.json",
            response_delay_seconds=5,
        )
    )

    assert delays == [5, 5]


def test_device_cli_defaults_to_demo_bundle(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["mqtt.device"])
    config = parse_device_args()
    assert config.response_registry == Path("demo_bundle/device/response.json")
    assert config.helper_registry == Path("demo_bundle/device/helper_data.json")


def test_insecure_device_path_warns(monkeypatch, tmp_path, capsys):
    _write_bundle(tmp_path)
    clients = []
    monkeypatch.setattr(
        "mqtt.device.mqtt.Client",
        lambda *a, **k: clients.append(DeviceClient()) or clients[-1],
    )
    run_device(DeviceConfig(insecure_key_hex="00" * 16))
    assert "WARNING" in capsys.readouterr().out


def test_server_classifies_rejection_categories():
    from auth.hmac_auth import PUFAuthenticator

    auth = PUFAuthenticator(time_window_seconds=60)
    key = b"k" * 16
    pending = {"device-001": {"nonce": "n", "timestamp": "1000"}}
    cases = [
        ({"uid": "other"}, "uid mismatch"),
        ({"uid": "device-001"}, "invalid challenge payload"),
        ({"uid": "device-001", "nonce": "n", "timestamp": "1000", "hmac": "bad"}, "tag mismatch"),
        ({"uid": "device-001", "nonce": "x", "timestamp": "1000", "hmac": "bad"}, "challenge mismatch"),
    ]
    for payload, expected in cases:
        reason, _, _ = classify_response(payload, "device-001", pending, auth, key, now=1000)
        assert reason == expected
    reason, _, _ = classify_response(
        {"uid": "device-001", "nonce": "x", "timestamp": "1000", "hmac": "bad"},
        "device-001", {}, auth, key, now=1000,
    )
    assert reason == "missing pending challenge"
    reason, _, _ = classify_response(
        {"uid": "device-001", "nonce": "n", "timestamp": "2000", "hmac": "bad"},
        "device-001", {"device-001": {"nonce": "n", "timestamp": "2000"}}, auth, key, now=1000,
    )
    assert reason == "timestamp future"
    reason, _, _ = classify_response(
        {"uid": "device-001", "nonce": "n", "timestamp": "900", "hmac": "bad"},
        "device-001", {"device-001": {"nonce": "n", "timestamp": "900"}}, auth, key, now=1000,
    )
    assert reason == "timestamp expired"
    auth.used_nonces["n"] = 999
    reason, _, _ = classify_response(
        {"uid": "device-001", "nonce": "n", "timestamp": "1000", "hmac": "bad"},
        "device-001", pending, auth, key, now=1000,
    )
    assert reason.startswith("replay")


@pytest.mark.parametrize(
    ("name", "payload_factory", "expected_log", "expects_result"),
    [
        (
            "uid_mismatch",
            lambda challenge, key: {"uid": "other", "nonce": "n", "timestamp": "1000", "hmac": "x"},
            "uid mismatch",
            False,
        ),
        (
            "payload_invalid",
            lambda challenge, key: RawMessage("iot/auth/response", b"not-json"),
            "invalid challenge payload",
            False,
        ),
        (
            "missing_pending",
            lambda challenge, key: {"uid": "device-001", "nonce": "n", "timestamp": "1000", "hmac": "x"},
            "missing pending challenge",
            True,
        ),
        (
            "challenge_mismatch",
            lambda challenge, key: {"uid": "device-001", "nonce": "different", "timestamp": "1000", "hmac": "x"},
            "challenge mismatch",
            True,
        ),
        (
            "timestamp_future",
            lambda challenge, key: {"uid": "device-001", "nonce": "n", "timestamp": "2000", "hmac": "x"},
            "timestamp future",
            True,
        ),
        (
            "timestamp_expired",
            lambda challenge, key: {"uid": "device-001", "nonce": "n", "timestamp": "900", "hmac": "x"},
            "timestamp expired",
            True,
        ),
        (
            "nonce_replay",
            lambda challenge, key: {
                "uid": "device-001",
                "nonce": challenge["nonce"],
                "timestamp": challenge["timestamp"],
                "hmac": server_module.PUFAuthenticator().generate_response(
                    key, "device-001", challenge
                ),
            },
            "replay",
            True,
        ),
        (
            "tag_mismatch",
            lambda challenge, key: {"uid": "device-001", "nonce": "n", "timestamp": "1000", "hmac": "x"},
            "tag mismatch",
            True,
        ),
    ],
)
def test_server_on_message_rejection_cases(
    monkeypatch, tmp_path, name, payload_factory, expected_log, expects_result
):
    monkeypatch.setattr(server_module.time, "time", lambda: 1000)
    if name == "timestamp_future":
        challenge = {"uid": "device-001", "nonce": "n", "timestamp": "2000"}
    elif name == "timestamp_expired":
        monkeypatch.setattr(server_module.time, "time", lambda: 1000)
        challenge = {"uid": "device-001", "nonce": "n", "timestamp": "900"}
    else:
        challenge = None

    repeat = 2 if name == "nonce_replay" else 1
    published, logs, callback, client, key, generated = _run_server_callback_case(
        monkeypatch,
        tmp_path,
        payload_factory,
        challenge=challenge,
        repeat=repeat,
        trigger=name != "missing_pending",
    )

    if name == "missing_pending":
        callback(client, None, Message("iot/auth/response", payload_factory(generated, key)))

    assert any(expected_log in entry for entry in logs)
    results = [value for topic, value in published if topic.endswith("/result")]
    if expects_result and name != "payload_invalid":
        assert results
        assert set(results[-1]) == {"uid", "nonce", "status"}
        assert results[-1]["status"] == "REJECT"
    if name == "uid_mismatch":
        assert not results


def test_server_callback_response_delay_reaches_timestamp_expired(monkeypatch, tmp_path):
    monkeypatch.setattr(server_module.time, "time", lambda: 1005)
    challenge = {"uid": "device-001", "nonce": "n", "timestamp": "1000"}

    def delayed_device_response(payload, key):
        return build_response_payload(
            server_module.PUFAuthenticator(time_window_seconds=3),
            key,
            "device-001",
            {"nonce": payload["nonce"], "timestamp": payload["timestamp"]},
        )

    published, logs, *_ = _run_server_callback_case(
        monkeypatch, tmp_path,
        delayed_device_response,
        challenge=challenge,
        config=ServerConfig(time_window_seconds=3, challenge_interval_seconds=0),
    )
    assert any("timestamp expired" in entry for entry in logs)
    results = [value for topic, value in published if topic.endswith("/result")]
    assert results and set(results[-1]) == {"uid", "nonce", "status"}
    assert results[-1]["status"] == "REJECT"


def test_wrong_device_reconstruction_uses_crossed_registries(tmp_path):
    extractor = FuzzyExtractor()
    mask = np.zeros(655360, dtype=np.uint8)
    mask[:2816] = 1
    golden_a = np.random.default_rng(10).integers(0, 2, 655360, dtype=np.uint8)
    golden_b = np.random.default_rng(11).integers(0, 2, 655360, dtype=np.uint8)
    key_a, helper_a = extractor.gen(golden_a, mask, "device-a", np.random.default_rng(12))
    extractor.gen(golden_b, mask, "device-b", np.random.default_rng(13))
    response_path = tmp_path / "response.json"
    helper_path = tmp_path / "helper.json"
    response_path.write_text(json.dumps({"device-b": {"response_bits": golden_b.tolist()}}))
    helper_path.write_text(json.dumps({"device-a": helper_a}))

    with pytest.raises((KeyError, ValueError)):
        resolve_reconstructed_key("device-a", response_path, helper_path)
