from auth.hmac_auth import generate_hmac, verify_hmac


def test_hmac_roundtrip() -> None:
    key = bytes.fromhex("00112233445566778899aabbccddeeff")
    challenge = b"challenge"
    nonce = b"nonce"
    tag = generate_hmac(key, challenge, nonce)
    assert verify_hmac(key, challenge, nonce, tag)
