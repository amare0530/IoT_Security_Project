import ecdsa
import pytest
from vrf_py.VRF import (
    generate_seed_salt_hash,
    generate_proof,
    generate_beta
)
from vrf_py.error import SeedError, VerificationError, InputError

class TestGenerateSeedSaltHash:

    def test_generate_seed_salt_hash_returns_tuple(self):
      """
      Test the function generate_seed_salt_hash to ensure it returns a tuple
      containing the seed, its hash, and the salt.

      Steps:
      1. Call the function under test to get the result.
      2. Assert that the result is a tuple.
      3. Assert that the first element (seed) is a string.
      4. Assert that the second element (seed_hash) is a string.

      Expected Outcome:
      The function should return a tuple with three elements: seed (string),
      seed_hash (string), and salt (bytes).
      """
      seed, seed_hash, _ = generate_seed_salt_hash()
      assert isinstance(seed, str)
      assert isinstance(seed_hash, str)

    def test_generate_seed_salt_hash_seed_is_hexadecimal_string(self):
      """
      Test the function generate_seed_salt_hash to ensure the generated seed
      is a valid hexadecimal string.

      Steps:
      1. Call the function under test to get the seed.
      2. Assert that every character in the seed is a valid hexadecimal character.

      Expected Outcome:
      The generated seed should be a valid hexadecimal string.
      """
      seed, _, _ = generate_seed_salt_hash()
      assert all(c in '0123456789abcdef' for c in seed)

    def test_algorithm_value(self, caplog):
        """
        Test the function generate_seed_salt_hash to ensure only valid
        hashing algorithm can be used

        Expected Outcome:
        ValueError
        """
        algorithm = 'fake_algorithm'
        with pytest.raises(ValueError):
            generate_seed_salt_hash(_algorithm=algorithm)
    
    def test_generate_seed_salt_hash_salt_is_bytes_object(self):
      """
      Test the function generate_seed_salt_hash to ensure the generated salt
      is a str object.

      Steps:
      1. Call the function under test to get the salt.
      2. Assert that the salt is a str object.

      Expected Outcome:
      The generated salt should be a str object.
      """
      _, _, salt = generate_seed_salt_hash()
      assert isinstance(salt, str)
  

    def test_generate_seed_salt_hash_algorithm_can_be_changed(self):
      """
      Test the function generate_seed_salt_hash to ensure the hashing algorithm
      used in the PBKDF2 function can be changed.

      Steps:
      1. Define a custom hashing algorithm.
      2. Call the function under test with the custom algorithm.
      3. Assert that the resulting seed_hash is different from the default.

      Expected Outcome:
      The seed_hash should be different when using a custom hashing algorithm.
      """
      algorithm = 'sha256'
      seed, seed_hash, _ = generate_seed_salt_hash(_algorithm=algorithm)
      assert seed_hash != generate_seed_salt_hash()[1]


    # Tests that generate_proof raises a VerificationError when given an invalid private key.
    def test_generate_proof_invalid_private_key(self):
        """
        Test the behavior of the generate_proof function when provided with an invalid private key.

        This test checks if the generate_proof function raises a VerificationError when given a string
        that is not a valid private key.
        """
        private_key = "invalid_key"
        alpha = b"test"
        with pytest.raises(VerificationError):
            generate_proof(private_key, alpha)

    # Tests that generate_proof raises a VerificationError when given an invalid alpha.
    def test_generate_proof_invalid_alpha(self):
        """
        Test the behavior of the generate_proof function when provided with an invalid alpha.

        This test checks if the generate_proof function raises a VerificationError when given a string
        instead of a bytes object for the alpha parameter.
        """
        private_key = ecdsa.keys.SigningKey.generate()
        alpha = "invalid_alpha"
        with pytest.raises(VerificationError):
            generate_proof(private_key, alpha)

    # Tests that generate_proof raises a VerificationError when given an alpha of length 0.
    def test_generate_proof_alpha_length_0(self):
        """
        Test the behavior of the generate_proof function when provided with an empty alpha.

        This test checks if the generate_proof function raises a VerificationError when given an alpha
        of length 0.
        """
        private_key = ecdsa.keys.SigningKey.generate()
        alpha = b""
        with pytest.raises(VerificationError):
            generate_proof(private_key, alpha)

    # Tests that generate_proof returns a valid proof when given an alpha of length equal to the maximum allowed.
    def test_generate_proof_alpha_length_maximum_allowed(self):
        """
        Test the behavior of the generate_proof function when provided with a large alpha.

        This test checks if the generate_proof function returns a valid proof (bytes object) when given
        an alpha of length equal to the maximum allowed.
        """
        private_key = ecdsa.keys.SigningKey.generate()
        alpha = b"test" * 1000000
        proof = generate_proof(private_key, alpha)
        assert isinstance(proof, bytes)


    # Tests that generate_beta returns a string.
    def test_generate_beta_returns_string(self):
        proof = b"proof"
        salt = "salt"
        seed_hash = 'seed_hash'
        result = generate_beta(proof, salt, seed_hash)
        assert isinstance(result, str)

    # Tests that generate_beta returns a string of length 64.
    def test_generate_beta_returns_string_of_length_64(self):
        proof = b"proof"
        salt = "salt"
        seed_hash = 'seed_hash'
        result = generate_beta(proof, salt, seed_hash)
        assert len(result) == 64

    # Tests that generate_beta returns a string containing only hexadecimal characters.
    def test_generate_beta_returns_string_with_only_hexadecimal_characters(self):
        proof = b"proof"
        salt = "salt"
        seed_hash = 'seed_hash'
        result = generate_beta(proof, salt, seed_hash)
        assert all(c in "0123456789abcdef" for c in result)

    # Tests that generate_beta returns the expected output for a given input.
    def test_generate_beta_returns_expected_output(self):
        proof = b"proof"
        salt = "salt"
        seed_hash = 'seed_hash'
        expected_output = "95bf8fc13c6cab0e6609b64deb34d32c10d74102763cfc35ffd4627050ba30b6"
        result = generate_beta(proof, salt, seed_hash)
        assert result == expected_output

    # Tests that generate_beta raises an exception if proof is None.
    def test_generate_beta_raises_exception_if_proof_is_none(self):
        proof = None
        salt = "salt"
        seed_hash = 'seed_hash'
        with pytest.raises(Exception):
            generate_beta(proof, salt, bullet_index)

    # Tests that generate_beta raises an exception if salt is None.
    def test_generate_beta_raises_exception_if_salt_is_none(self):
        proof = b"proof"
        salt = None
        seed_hash = 'seed_hash'
        with pytest.raises(Exception):
            generate_beta(proof, salt, bullet_index)