from auth.hmac_auth import PUFAuthenticator
from mqtt.device import build_response_payload
from mqtt.server import build_challenge_payload, extract_challenge


def test_mqtt_challenge_response_payload_roundtrip() -> None:
    authenticator = PUFAuthenticator(time_window_seconds=60)
    uid = "device-001"
    key = bytes.fromhex("00112233445566778899aabbccddeeff")

    challenge_payload = build_challenge_payload(authenticator, uid)
    response_payload = build_response_payload(
        authenticator=authenticator,
        secret_key=key,
        uid=uid,
        challenge=extract_challenge(challenge_payload),
    )

    assert response_payload["uid"] == uid
    assert response_payload["nonce"] == challenge_payload["nonce"]
    assert response_payload["timestamp"] == challenge_payload["timestamp"]

    is_valid, _ = authenticator.verify_response(
        expected_key=key,
        uid=uid,
        challenge=extract_challenge(response_payload),
        device_response=response_payload["hmac"],
    )

    assert is_valid is True
