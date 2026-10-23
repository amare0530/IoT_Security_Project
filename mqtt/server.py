from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import dataclass
from pathlib import Path

import paho.mqtt.client as mqtt

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from auth.hmac_auth import PUFAuthenticator
from puf.key_provider import DEFAULT_KEY_REGISTRY, resolve_key_bytes


@dataclass
class ServerConfig:
    broker: str = "localhost"
    port: int = 1883
    uid: str = "device-001"
    challenge_topic: str = "iot/auth/challenge"
    response_topic: str = "iot/auth/response"
    result_topic: str = "iot/auth/result"
    secret_key_hex: str | None = None
    key_registry: Path = DEFAULT_KEY_REGISTRY
    time_window_seconds: int = 60
    challenge_interval_seconds: int = 5


def build_challenge_payload(
    authenticator: PUFAuthenticator, uid: str
) -> dict[str, str]:
    challenge = authenticator.generate_challenge()
    return {
        "uid": uid,
        "nonce": challenge["nonce"],
        "timestamp": challenge["timestamp"],
    }


def extract_challenge(payload: dict[str, str]) -> dict[str, str]:
    return {
        "nonce": payload["nonce"],
        "timestamp": payload["timestamp"],
    }


def run_server(config: ServerConfig) -> None:
    secret_key = resolve_key_bytes(
        uid=config.uid,
        manual_key_hex=config.secret_key_hex,
        registry_path=config.key_registry,
    )
    authenticator = PUFAuthenticator(time_window_seconds=config.time_window_seconds)
    pending_challenges: dict[str, dict[str, str]] = {}
    authenticated = False

    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="puf-server")

    def publish_challenge() -> None:
        payload = build_challenge_payload(authenticator, config.uid)
        pending_challenges[config.uid] = extract_challenge(payload)
        client.publish(config.challenge_topic, json.dumps(payload), qos=1)
        print(
            f"Server published challenge for uid={config.uid} "
            f"nonce={payload['nonce'][:8]}..."
        )

    def publish_result(uid: str, accepted: bool) -> None:
        client.publish(
            config.result_topic,
            json.dumps({"uid": uid, "status": "ACCEPT" if accepted else "REJECT"}),
            qos=1,
        )

    def on_connect(client: mqtt.Client, userdata, flags, reason_code, properties):
        client.subscribe(config.response_topic, qos=1)
        print(f"Server connected and subscribed to {config.response_topic}")

    def on_message(client: mqtt.Client, userdata, message: mqtt.MQTTMessage):
        nonlocal authenticated
        try:
            payload = json.loads(message.payload.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            print("Server ignored malformed MQTT payload")
            return
        if not isinstance(payload, dict):
            print("Server ignored non-object MQTT payload")
            return
        uid = payload.get("uid", "")

        if uid != config.uid:
            print(f"REJECT uid mismatch: uid={uid}")
            publish_result(str(uid), False)
            return

        try:
            challenge = extract_challenge(payload)
        except (KeyError, TypeError):
            print(f"REJECT invalid challenge payload: uid={uid}")
            publish_result(uid, False)
            return

        nonce = challenge.get("nonce")
        if nonce in authenticator.used_nonces:
            print(f"REJECT replay: nonce already used: uid={uid}")
            publish_result(uid, False)
            return

        expected_challenge = pending_challenges.get(uid)
        if expected_challenge is None:
            print(f"REJECT missing pending challenge: uid={uid}")
            publish_result(uid, False)
            return
        if challenge != expected_challenge:
            print(f"REJECT challenge mismatch: uid={uid}")
            publish_result(uid, False)
            return

        try:
            challenge_time = int(challenge["timestamp"])
        except (KeyError, TypeError, ValueError):
            print(f"REJECT invalid timestamp: uid={uid}")
            publish_result(uid, False)
            return
        current_time = int(time.time())
        if challenge_time > current_time:
            print(f"REJECT timestamp future: uid={uid}")
        elif current_time - challenge_time > authenticator.time_window:
            print(f"REJECT timestamp expired: uid={uid}")

        is_valid, msg = authenticator.verify_response(
            expected_key=secret_key,
            uid=uid,
            challenge=challenge,
            device_response=payload.get("hmac", ""),
        )
        print(f"Authentication valid={is_valid} for uid={uid}: {msg}")

        if is_valid:
            authenticated = True
            del pending_challenges[uid]
        elif "HMAC" in msg or "signature" in msg:
            print(f"REJECT tag mismatch: uid={uid}")
        publish_result(uid, is_valid)

    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(config.broker, config.port, keepalive=60)
    client.loop_start()

    try:
        while True:
            if not authenticated and client.is_connected():
                publish_challenge()
            time.sleep(config.challenge_interval_seconds)
    except KeyboardInterrupt:
        print("Server stopped")
    finally:
        client.loop_stop()
        client.disconnect()


def parse_args() -> ServerConfig:
    parser = argparse.ArgumentParser(description="PUF MQTT server demo")
    parser.add_argument("--broker", default="localhost")
    parser.add_argument("--port", type=int, default=1883)
    parser.add_argument("--uid", default="device-001")
    parser.add_argument("--key", default=None)
    parser.add_argument("--key-registry", type=Path, default=DEFAULT_KEY_REGISTRY)
    parser.add_argument("--challenge-topic", default="iot/auth/challenge")
    parser.add_argument("--response-topic", default="iot/auth/response")
    parser.add_argument("--result-topic", default="iot/auth/result")
    parser.add_argument("--time-window", type=int, default=60)
    parser.add_argument("--challenge-interval", type=int, default=5)
    args = parser.parse_args()
    return ServerConfig(
        broker=args.broker,
        port=args.port,
        uid=args.uid,
        secret_key_hex=args.key,
        key_registry=args.key_registry,
        challenge_topic=args.challenge_topic,
        response_topic=args.response_topic,
        result_topic=args.result_topic,
        time_window_seconds=args.time_window,
        challenge_interval_seconds=args.challenge_interval,
    )


if __name__ == "__main__":
    run_server(parse_args())
