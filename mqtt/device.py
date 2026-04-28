from __future__ import annotations

import json
from dataclasses import dataclass

import paho.mqtt.client as mqtt

from auth.hmac_auth import generate_hmac


@dataclass
class DeviceConfig:
    broker: str = "localhost"
    port: int = 1883
    challenge_topic: str = "iot/auth/challenge"
    response_topic: str = "iot/auth/response"
    secret_key_hex: str = "00112233445566778899aabbccddeeff"


def run_device(config: DeviceConfig) -> None:
    secret_key = bytes.fromhex(config.secret_key_hex)

    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="puf-device")

    def on_connect(client: mqtt.Client, userdata, flags, reason_code, properties):
        client.subscribe(config.challenge_topic)
        print("Device connected and subscribed")

    def on_message(client: mqtt.Client, userdata, message: mqtt.MQTTMessage):
        payload = json.loads(message.payload.decode("utf-8"))
        challenge = bytes.fromhex(payload["challenge"])
        nonce = bytes.fromhex(payload["nonce"])
        hmac_hex = generate_hmac(secret_key, challenge, nonce)
        response = {
            "uid": payload.get("uid", "device-001"),
            "hmac": hmac_hex,
            "challenge": payload["challenge"],
            "nonce": payload["nonce"],
        }
        client.publish(config.response_topic, json.dumps(response), qos=1)
        print("Device published response")

    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(config.broker, config.port, keepalive=60)
    client.loop_forever()


if __name__ == "__main__":
    run_device(DeviceConfig())
