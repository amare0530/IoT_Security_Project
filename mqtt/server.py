from __future__ import annotations

import json
import secrets
from dataclasses import dataclass

import paho.mqtt.client as mqtt

from auth.hmac_auth import verify_hmac


@dataclass
class ServerConfig:
    broker: str = "localhost"
    port: int = 1883
    challenge_topic: str = "iot/auth/challenge"
    response_topic: str = "iot/auth/response"
    secret_key_hex: str = "00112233445566778899aabbccddeeff"


def run_server(config: ServerConfig) -> None:
    secret_key = bytes.fromhex(config.secret_key_hex)
    challenge = secrets.token_bytes(16)
    nonce = secrets.token_bytes(16)

    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="puf-server")

    def on_connect(client: mqtt.Client, userdata, flags, reason_code, properties):
        client.subscribe(config.response_topic)
        payload = {
            "uid": "device-001",
            "challenge": challenge.hex(),
            "nonce": nonce.hex(),
        }
        client.publish(config.challenge_topic, json.dumps(payload), qos=1)
        print("Server published challenge")

    def on_message(client: mqtt.Client, userdata, message: mqtt.MQTTMessage):
        payload = json.loads(message.payload.decode("utf-8"))
        is_valid = verify_hmac(
            secret_key=secret_key,
            challenge=bytes.fromhex(payload["challenge"]),
            nonce=bytes.fromhex(payload["nonce"]),
            expected_hex=payload["hmac"],
        )
        print(f"Authentication valid={is_valid} for uid={payload.get('uid', 'unknown')}")

    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(config.broker, config.port, keepalive=60)
    client.loop_forever()


if __name__ == "__main__":
    run_server(ServerConfig())
