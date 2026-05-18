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

    def on_connect(client: mqtt.Client, userdata, flags, reason_code, properties):
        client.subscribe(config.response_topic, qos=1)
        print(f"Server connected and subscribed to {config.response_topic}")

    def on_message(client: mqtt.Client, userdata, message: mqtt.MQTTMessage):
        nonlocal authenticated
        payload = json.loads(message.payload.decode("utf-8"))
        uid = payload.get("uid", "")

        if uid != config.uid:
            print(f"Authentication valid=False for uid={uid}: unknown uid")
            return

        try:
            challenge = extract_challenge(payload)
            expected_challenge = pending_challenges[uid]
        except KeyError:
            print(f"Authentication valid=False for uid={uid}: missing challenge")
            return

        if challenge != expected_challenge:
            print(f"Authentication valid=False for uid={uid}: challenge mismatch")
            return

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
        time_window_seconds=args.time_window,
        challenge_interval_seconds=args.challenge_interval,
    )


if __name__ == "__main__":
    run_server(parse_args())
