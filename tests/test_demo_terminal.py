import inspect
import json
import re
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

from auth.hmac_auth import PUFAuthenticator
from demo import device as demo_device
from demo import hacker as demo_hacker
from demo import server as demo_server
from demo.make_synthetic_bundle import OTHER_UID, UID, write_bundle
from mqtt.server import classify_response
from puf.fuzzy_extractor import FuzzyExtractor
from puf.key_provider import load_reconstruction_inputs, resolve_reconstructed_key

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def bundle(tmp_path_factory):
    out = tmp_path_factory.mktemp("bundle")
    key = write_bundle(out, seed=11)
    bits, helper = load_reconstruction_inputs(
        UID, out / "device" / "response.json", out / "device" / "helper_data.json"
    )
    return out, key, bits, helper


def test_every_server_reject_reason_maps_to_a_gate():
    source = inspect.getsource(classify_response)
    reasons = set(re.findall(r'return "([^"]+)"', source))
    mapped = {reason for _, group in demo_server.GATES for reason in group}
    assert reasons and reasons == mapped
    assert demo_server.gate_index(None) is None
    assert demo_server.gate_index("uid mismatch") == 1
    assert demo_server.gate_index("tag mismatch") == 5
    for reason in reasons:
        path, line = demo_server.source_line(reason).split(":")
        text = (ROOT / path).read_text(encoding="utf-8").splitlines()[int(line) - 1]
        assert reason in text


def test_vote_tally_agrees_with_real_rep(bundle):
    _, key, bits, helper = bundle
    votes = demo_device.vote_tally(bits, helper)
    assert votes.shape == (256,)
    key_bits = (votes > helper["repetition"] / 2).astype(np.uint8)
    assert FuzzyExtractor._bits_to_key(key_bits, helper["uid"]) == key
    assert FuzzyExtractor().rep(bits, helper) == key
    losing = demo_device.dissent(votes, helper["repetition"])
    assert losing.max() <= 5 and (losing > 0).any()


def test_noise_is_applied_to_a_copy_and_heavy_noise_breaks_the_key(bundle):
    _, key, bits, helper = bundle
    indices = np.asarray(helper["stable_indices"], dtype=np.int64)
    rng = np.random.default_rng(3)
    same, flipped = demo_device.add_noise(bits, indices, 0.0, rng)
    assert flipped == 0 and np.array_equal(same, bits) and same is not bits
    light, flipped = demo_device.add_noise(bits, indices, 0.03, rng)
    assert 0 < flipped < 200
    assert FuzzyExtractor().rep(light, helper) == key
    heavy, _ = demo_device.add_noise(bits, indices, 0.45, rng)
    assert FuzzyExtractor().rep(heavy, helper) != key


def test_other_chip_with_stolen_helper_data_gives_a_different_key(bundle):
    out, key, _, helper = bundle
    other = demo_device.load_other_chip(out / "attacker" / "response.json")
    assert other.shape == (655_360,)
    assert FuzzyExtractor().rep(other, helper) != key
    assert OTHER_UID != UID


def test_uid_autodetection(bundle):
    out, _, _, _ = bundle
    assert demo_device.only_uid_in_helper(out / "device" / "helper_data.json") == UID
    assert demo_server.only_uid_in_registry(out / "server" / "key_registry.csv") == UID
    device_text = b"".join(path.read_bytes() for path in (out / "device").iterdir())
    assert b"key_hex" not in device_text


def test_public_loader_matches_existing_reconstruction(bundle):
    out, key, _, _ = bundle
    assert resolve_reconstructed_key(
        UID, out / "device" / "response.json", out / "device" / "helper_data.json"
    ) == key


def test_weak_pin_and_hacker_packet_helpers():
    assert demo_server.check_pin("0042", "0042")
    assert not demo_server.check_pin("0042", "0043")
    assert not demo_server.check_pin("0042", 42)
    challenge = {"uid": "d", "nonce": "n", "timestamp": "5"}
    packet = demo_hacker.build_packet(challenge, "tag")
    assert packet == {"uid": "d", "nonce": "n", "timestamp": "5", "hmac": "tag"}
    assert demo_hacker.edit_packet(packet, "uid", "other")["uid"] == "other"
    assert len(demo_hacker.edit_packet(packet, "hmac", "")["hmac"]) == 64
    assert packet["uid"] == "d"
    with pytest.raises(ValueError):
        demo_hacker.edit_packet(packet, "key", "x")


class _Client:
    def __init__(self):
        self.published = []

    def publish(self, topic, payload, **kwargs):
        self.published.append((topic, json.loads(payload)))


def _demo_server(bundle_dir, monkeypatch):
    client = _Client()
    monkeypatch.setattr(demo_server.mqtt, "Client", lambda *a, **k: client)
    args = demo_server.parse_args(
        ["--key-registry", str(bundle_dir / "server" / "key_registry.csv"), "--fast"]
    )
    return demo_server.DemoServer(args), client


def test_demo_server_accepts_real_device_then_rejects_replay_and_forgery(
    bundle, monkeypatch, capsys
):
    out, key, _, _ = bundle
    server, client = _demo_server(out, monkeypatch)
    auth = PUFAuthenticator()

    server.publish_challenge()
    challenge = client.published[-1][1]
    good = {**challenge, "hmac": auth.generate_response(key, UID, challenge)}
    server.handle_response(good)
    assert client.published[-1] == (
        "iot/auth/result", {"uid": UID, "nonce": challenge["nonce"], "status": "ACCEPT"}
    )

    server.handle_response(good)
    assert client.published[-1][1]["status"] == "REJECT"

    server.publish_challenge()
    fresh = client.published[-1][1]
    server.handle_response({**fresh, "hmac": "00" * 32})
    assert client.published[-1][1] == {
        "uid": UID, "nonce": fresh["nonce"], "status": "REJECT"
    }
    before = len(client.published)
    server.handle_response({**fresh, "uid": "someone-else", "hmac": "00" * 32})
    server.handle_response("not an object")
    assert len(client.published) == before
    assert (server.accepted, server.rejected) == (1, 4)

    text = capsys.readouterr().out
    assert "ACCEPT" in text and "nonce already used" in text and "tag mismatch" in text
    assert key.hex() not in text


def test_demo_server_weak_baseline_is_separate_from_real_protocol(bundle, monkeypatch):
    out, _, _, _ = bundle
    server, client = _demo_server(out, monkeypatch)
    server.weak_pin = "0007"
    server.handle_weak_login({"pin": "0001"})
    server.handle_weak_login({"pin": "0007"})
    assert [payload["status"] for _, payload in client.published] == ["REJECT", "ACCEPT"]
    assert {topic for topic, _ in client.published} == {"iot/weak/result"}


def test_export_bundle_can_add_another_devices_boot(tmp_path):
    from tests.test_export_demo_bundle import SCRIPT, _write_dataset

    crps = tmp_path / "crps.csv"
    out = tmp_path / "bundle"
    _write_dataset(crps, uids=("demo-uid", "other-uid"))
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--uid", "demo-uid", "--crps", str(crps),
         "--out", str(out), "--train-boots", "2", "--selection", "legacy",
         "--seed", "7", "--attacker-uid", "other-uid"],
        cwd=ROOT, text=True, capture_output=True,
    )
    assert result.returncode == 0, result.stderr
    assert "wrong-chip check" in result.stdout and "matches registered=no" in result.stdout
    attacker = json.loads((out / "attacker" / "response.json").read_text())
    assert list(attacker) == ["other-uid"]
    assert len(attacker["other-uid"]["response_bits"]) == 655_360
    assert not (out / "attacker" / "helper_data.json").exists()

    same = subprocess.run(
        [sys.executable, str(SCRIPT), "--uid", "demo-uid", "--crps", str(crps),
         "--out", str(out), "--train-boots", "2", "--selection", "legacy",
         "--attacker-uid", "demo-uid"],
        cwd=ROOT, text=True, capture_output=True,
    )
    assert same.returncode == 1
