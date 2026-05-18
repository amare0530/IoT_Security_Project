from __future__ import annotations

import hashlib
import hmac
import secrets
import time
from typing import Dict, Tuple


class PUFAuthenticator:
    """
    Challenge-response authentication for SRAM PUF derived keys.

    The signed payload is uid:nonce:timestamp. Nonce prevents response reuse,
    timestamp bounds replay windows, and compare_digest avoids timing leaks.
    """

    def __init__(self, time_window_seconds: int = 60):
        if time_window_seconds <= 0:
            raise ValueError("time_window_seconds must be positive")
        self.time_window = time_window_seconds
        self.used_nonces: dict[str, int] = {}

    def generate_challenge(self) -> Dict[str, str]:
        return {
            "nonce": secrets.token_hex(16),
            "timestamp": str(int(time.time())),
        }

    def generate_response(self, key: bytes, uid: str, challenge: Dict[str, str]) -> str:
        payload = self._build_payload(uid, challenge)
        return hmac.new(key, payload, hashlib.sha256).hexdigest()

    def verify_response(
        self,
        expected_key: bytes,
        uid: str,
        challenge: Dict[str, str],
        device_response: str,
    ) -> Tuple[bool, str]:
        try:
            challenge_time = int(challenge["timestamp"])
            nonce = challenge["nonce"]
        except (KeyError, TypeError, ValueError):
            return False, "Authentication Failed: Invalid challenge payload."

        current_time = int(time.time())
        self._prune_used_nonces(current_time)

        if abs(current_time - challenge_time) > self.time_window:
            return False, "Authentication Failed: Challenge expired (Possible Replay Attack)."

        if nonce in self.used_nonces:
            return False, "Authentication Failed: Nonce already used (Replay Attack)."

        try:
            expected_response = self.generate_response(expected_key, uid, challenge)
        except KeyError:
            return False, "Authentication Failed: Invalid challenge payload."

        if hmac.compare_digest(expected_response, device_response):
            self.used_nonces[nonce] = current_time
            return True, "Authentication Successful."
        return False, "Authentication Failed: Invalid HMAC signature."

    def _prune_used_nonces(self, current_time: int) -> None:
        expired = [
            nonce
            for nonce, used_at in self.used_nonces.items()
            if current_time - used_at > self.time_window
        ]
        for nonce in expired:
            del self.used_nonces[nonce]

    @staticmethod
    def _build_payload(uid: str, challenge: Dict[str, str]) -> bytes:
        return f"{uid}:{challenge['nonce']}:{challenge['timestamp']}".encode("utf-8")


def generate_hmac(secret_key: bytes, challenge: bytes, nonce: bytes) -> str:
    """Backward-compatible helper used by the current MQTT prototype."""
    message = challenge + nonce
    return hmac.new(secret_key, message, hashlib.sha256).hexdigest()


def verify_hmac(
    secret_key: bytes, challenge: bytes, nonce: bytes, expected_hex: str
) -> bool:
    computed = generate_hmac(secret_key, challenge, nonce)
    return hmac.compare_digest(computed, expected_hex)
