from __future__ import annotations

import hmac
import hashlib


def generate_hmac(secret_key: bytes, challenge: bytes, nonce: bytes) -> str:
    message = challenge + nonce
    return hmac.new(secret_key, message, hashlib.sha256).hexdigest()


def verify_hmac(secret_key: bytes, challenge: bytes, nonce: bytes, expected_hex: str) -> bool:
    computed = generate_hmac(secret_key, challenge, nonce)
    return hmac.compare_digest(computed, expected_hex)
