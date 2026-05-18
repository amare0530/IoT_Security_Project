import time
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from auth.hmac_auth import PUFAuthenticator, generate_hmac, verify_hmac


def test_hmac_roundtrip() -> None:
    key = bytes.fromhex("00112233445566778899aabbccddeeff")
    challenge = b"challenge"
    nonce = b"nonce"
    tag = generate_hmac(key, challenge, nonce)
    assert verify_hmac(key, challenge, nonce, tag)


def test_puf_authentication_flow() -> None:
    uid = "3038470130373036003B0034"
    correct_key = bytes.fromhex("14a20aff8f2da0387f6a42a92ed1a957")
    wrong_key = bytes.fromhex("99999999999999999999999999999999")

    print("\n--- Test 1: normal authentication with correct key ---")
    auth = PUFAuthenticator(time_window_seconds=5)
    challenge = auth.generate_challenge()
    device_response = auth.generate_response(correct_key, uid, challenge)
    is_valid, msg = auth.verify_response(correct_key, uid, challenge, device_response)
    assert is_valid is True
    print(msg)

    print("\n--- Test 2: wrong key / impersonation attempt ---")
    auth = PUFAuthenticator(time_window_seconds=5)
    challenge = auth.generate_challenge()
    bad_response = auth.generate_response(wrong_key, uid, challenge)
    is_valid, msg = auth.verify_response(correct_key, uid, challenge, bad_response)
    assert is_valid is False
    assert "Invalid HMAC" in msg
    print(msg)

    print("\n--- Test 3: tampered challenge / MITM attempt ---")
    auth = PUFAuthenticator(time_window_seconds=5)
    challenge = auth.generate_challenge()
    device_response = auth.generate_response(correct_key, uid, challenge)
    fake_challenge = challenge.copy()
    fake_challenge["nonce"] = "00000000000000000000000000000000"
    is_valid, msg = auth.verify_response(correct_key, uid, fake_challenge, device_response)
    assert is_valid is False
    assert "Invalid HMAC" in msg
    print(msg)

    print("\n--- Test 4: replay attack with expired timestamp ---")
    strict_auth = PUFAuthenticator(time_window_seconds=1)
    old_challenge = strict_auth.generate_challenge()
    old_response = strict_auth.generate_response(correct_key, uid, old_challenge)
    time.sleep(2)
    is_valid, msg = strict_auth.verify_response(
        correct_key, uid, old_challenge, old_response
    )
    assert is_valid is False
    assert "expired" in msg
    print(msg)

    print("\n--- Test 5: immediate replay with reused nonce ---")
    auth = PUFAuthenticator(time_window_seconds=5)
    challenge = auth.generate_challenge()
    device_response = auth.generate_response(correct_key, uid, challenge)
    is_valid, msg = auth.verify_response(correct_key, uid, challenge, device_response)
    assert is_valid is True
    replay_valid, replay_msg = auth.verify_response(
        correct_key, uid, challenge, device_response
    )
    assert replay_valid is False
    assert "Nonce already used" in replay_msg
    print(replay_msg)


if __name__ == "__main__":
    test_puf_authentication_flow()
