import time
import hashlib
import unittest
import ecdsa
from vrf_py.VRF import (
  new_game,
  verify,
  ALGO,
  ITERATIONS
)


class TestIntegration(unittest.TestCase):

  def test_vrf_various_scenarios(self):
    """
    Test the VRF system end-to-end for various scenarios to ensure
    consistent and correct behavior across different inputs.

    Steps:
    1. Define multiple scenarios with varying revolver sizes and bets.
    2. For each scenario:
        a. Generate a timestamp and convert the bets to a byte-encoded alpha.
        b. Generate a private key for signing.
        c. Initialize a new game to get seed, seed_hash, salt, beta, proof, bullet_index, bullet_index_hash, public_key_pem.
        d. Verify the outcome of the game using the provided values.
        e. Assert that the verification result is True and hashes match.

    Expected Outcome:
    The VRF system should correctly verify the outcome for each scenario,
    returning True for each verification.
    """

    # Step 1: Define multiple scenarios with varying revolver sizes and bets.
    scenarios = [
      {
        "revolver_size": 50,
        "bets": [30000, 30000, 30000, 30000]
      },
      {
        "revolver_size": 6,
        "bets": [100, 200, 300]
      },
      {
        "revolver_size": 10,
        "bets": [500, 1000, 1500, 2000, 2500]
      },
      {
        "revolver_size": 25,
        "bets": [50, 100, 150, 200]
      },
      {
        "revolver_size": 2,
        "bets": [100, 100]
      }
    ]

    for scenario in scenarios:
      # Step 2a: Generate a timestamp and convert the bets to a byte-encoded alpha.
      timestamp = str(int(time.time()))
      alpha_raw = (timestamp + ''.join(map(str, scenario["bets"])))
      alpha = alpha_raw.encode()

      # Step 2b: Generate a private key for signing.
      sk = ecdsa.SigningKey.generate(curve=ecdsa.SECP256k1)

      # Step 2c: Initialize a new game
      seed, seed_hash, salt, beta, proof, bullet_index, bullet_index_hash, public_key_pem = new_game(scenario['revolver_size'], sk, alpha)

      # Step 2d: Verify the outcome of the game using the provided values.
      proof_validity, derived_bullet_index_hash = verify(public_key_pem, seed_hash, salt, proof, bullet_index_hash, alpha, scenario['revolver_size'], beta)

      # Step 2e: Assert that the verification result is True.
      self.assertTrue(proof_validity, True)
      self.assertEqual(derived_bullet_index_hash, bullet_index_hash)
