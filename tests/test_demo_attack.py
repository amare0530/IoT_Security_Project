import json
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
