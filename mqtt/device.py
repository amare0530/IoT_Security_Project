from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path

import paho.mqtt.client as mqtt

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from auth.hmac_auth import PUFAuthenticator
from puf.key_provider import DEFAULT_KEY_REGISTRY, resolve_key_bytes


@dataclass
class DeviceConfig:
    broker: str = "localhost"
    port: int = 1883
    uid: str = "device-001"
    challenge_topic: str = "iot/auth/challenge"
    response_topic: str = "iot/auth/response"
    secret_key_hex: str | None = None
    key_registry: Path = DEFAULT_KEY_REGISTRY


def build_response_payload(
    authenticator: PUFAuthenticator,
    secret_key: bytes,
    uid: str,
    challenge: dict[str, str],
) -> dict[str, str]:
    return {
        "uid": uid,
        "nonce": challenge["nonce"],
        "timestamp": challenge["timestamp"],
        "hmac": authenticator.generate_response(secret_key, uid, challenge),
    }


def run_device(config: DeviceConfig) -> None:
    secret_key = resolve_key_bytes(
        uid=config.uid,
        manual_key_hex=config.secret_key_hex,
        registry_path=config.key_registry,
    )
    authenticator = PUFAuthenticator()

    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=f"puf-device-{config.uid}")

    def on_connect(client: mqtt.Client, userdata, flags, reason_code, properties):
        client.subscribe(config.challenge_topic, qos=1)
        print(f"Device {config.uid} connected and subscribed to {config.challenge_topic}")

    def on_message(client: mqtt.Client, userdata, message: mqtt.MQTTMessage):
        payload = json.loads(message.payload.decode("utf-8"))
        if payload.get("uid") != config.uid:
            return

        challenge = {
            "nonce": payload["nonce"],
            "timestamp": payload["timestamp"],
        }
        response = build_response_payload(
            authenticator=authenticator,
            secret_key=secret_key,
            uid=config.uid,
            challenge=challenge,
        )
        client.publish(config.response_topic, json.dumps(response), qos=1)
        print(f"Device {config.uid} published HMAC response")

    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(config.broker, config.port, keepalive=60)
    client.loop_forever()


def parse_args() -> DeviceConfig:
    parser = argparse.ArgumentParser(description="PUF MQTT device demo")
    parser.add_argument("--broker", default="localhost")
    parser.add_argument("--port", type=int, default=1883)
    parser.add_argument("--uid", default="device-001")
    parser.add_argument("--key", default=None)
    parser.add_argument("--key-registry", type=Path, default=DEFAULT_KEY_REGISTRY)
    parser.add_argument("--challenge-topic", default="iot/auth/challenge")
    parser.add_argument("--response-topic", default="iot/auth/response")
    args = parser.parse_args()
    return DeviceConfig(
        broker=args.broker,
        port=args.port,
        uid=args.uid,
        secret_key_hex=args.key,
        key_registry=args.key_registry,
        challenge_topic=args.challenge_topic,
        response_topic=args.response_topic,
    )


if __name__ == "__main__":
    run_device(parse_args())
