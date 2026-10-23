import json
import threading
import time
from argparse import Namespace

from scripts.demo_attack import (
    _publish,
    expired_payload,
    forge_payload,
    tamper_payload,
)


class FakeClient:
    def __init__(self):
        self.published = []

    def publish(self, topic, payload, **kwargs):
        self.published.append((topic, json.loads(payload)))


def test_attack_publish_format_contains_no_key_material():
    client = FakeClient()
    payload = {"uid": "demo", "nonce": "nonce-value", "timestamp": "1", "hmac": "0" * 64}
    _publish(client, "iot/auth/response", payload, "forge")
    topic, value = client.published[0]
    assert topic.endswith("/response")
    assert value["uid"] == "demo"
    assert set(value) == {"uid", "nonce", "timestamp", "hmac"}
    assert "key" not in json.dumps(value).lower()


def test_attack_modes_are_explicit():
    for mode in ("replay", "forge", "tamper", "expired"):
        args = Namespace(mode=mode, uid="demo", timeout=1)
        assert args.mode in {"replay", "forge", "tamper", "expired"}


def test_each_attack_payload_has_expected_shape():
    challenge = {"nonce": "n", "timestamp": "123"}
    forged = forge_payload("demo", challenge)
    assert set(forged) == {"uid", "nonce", "timestamp", "hmac"}
    original = {"uid": "demo", "nonce": "old", "timestamp": "123", "hmac": "tag"}
    tampered = tamper_payload(original)
    assert tampered["uid"] == original["uid"]
    assert tampered["timestamp"] == original["timestamp"]
    assert tampered["hmac"] == original["hmac"]
    assert tampered["nonce"] != original["nonce"]
    expired = expired_payload("demo", 60)
    assert int(expired["timestamp"]) < 0 or len(expired["hmac"]) == 64


def test_forge_waits_for_delayed_connack_and_challenge(monkeypatch):
    from scripts import demo_attack

    class Message:
        topic = "iot/auth/challenge"
        payload = json.dumps({"uid": "demo", "nonce": "n", "timestamp": "123"}).encode()

    class DelayedClient:
        instance = None

        def __init__(self, *args, **kwargs):
            DelayedClient.instance = self
            self.on_connect = None
            self.on_message = None
            self.published = []

        def subscribe(self, *args, **kwargs):
            pass

        def publish(self, topic, payload, **kwargs):
            self.published.append((topic, json.loads(payload)))

        def connect(self, *args, **kwargs):
            def notify():
                self.on_connect(self, None, None, 0, None)
                time.sleep(0.01)
                self.on_message(self, None, Message())

            threading.Timer(0.05, notify).start()

        def loop_start(self):
            pass

        def loop_stop(self):
            pass

        def disconnect(self):
            pass

    monkeypatch.setattr(demo_attack.mqtt, "Client", DelayedClient)
    args = Namespace(
        mode="forge",
        broker="localhost",
        port=1883,
        uid="demo",
        timeout=1,
        time_window=60,
        challenge_topic="iot/auth/challenge",
        response_topic="iot/auth/response",
    )
    demo_attack.run_attack(args)
    assert DelayedClient.instance.published
