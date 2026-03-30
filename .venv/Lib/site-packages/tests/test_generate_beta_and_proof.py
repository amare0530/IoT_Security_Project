import pytest
import ecdsa
import hashlib
from unittest.mock import patch, MagicMock
from vrf_py.VRF import (
    generate_beta_and_proof,
    ITERATIONS,
    ALGO,
    generate_proof,
    generate_beta
)
from vrf_py.error import VerificationError



class TestGenerateBetaAndProof:

    # Tests that generate_beta_and_proof returns a tuple containing beta, proof, and derived chamber index.
    def test_generate_beta_and_proof_returns_tuple(self):
        """
        Test the function generate_beta_and_proof to ensure
        it returns a tuple with the correct structure and types.

        Steps:
        1. Generate a private key for testing.
        2. Define the test inputs.
        3. Call the function under test to get the result.
        4. Assert that the result is a tuple.
        5. Assert that the tuple has exactly three elements.
        6. Assert that the first element (beta) is a string.
        7. Assert that the second element (proof) is bytes.
        8. Assert that the third element (derived chamber index)
           is an integer.

        Expected Outcome:
        The function should return a tuple with three elements: beta
        (string), proof (bytes), and derived chamber index (integer).
        """

        # Step 1: Generate a private key for testing.
        private_key = ecdsa.SigningKey.generate(curve=ecdsa.SECP256k1)

        # Step 2: Define the test inputs.
        alpha = b"input message"
        bullet_index = 0
        salt = "salt"
        seed_hash = 'seed_hash'
        revolver_chambers = 6

        # Step 3: Call the function under test to get the result.
        result = generate_beta_and_proof(private_key, alpha, seed_hash, salt, revolver_chambers)

        # Step 4: Assert that the result is a tuple.
        assert isinstance(result, tuple)

        # Step 5: Assert that the tuple has exactly three elements.
        assert len(result) == 3

        # Step 6: Assert that the first element (beta) is a string.
        assert isinstance(result[0], str)

        # Step 7: Assert that the second element (proof) is bytes.
        assert isinstance(result[1], bytes)

        # Step 8: Assert that the third element (derived chamber index) is an integer.
        assert isinstance(result[2], int)


    # Tests that generate_beta_and_proof generates a valid proof.
    def test_generate_beta_and_proof_generates_valid_proof(self):
        """
        Test the function generate_beta_and_proof to ensure
        it correctly generates a valid proof.

        Steps:
        1. Generate a private key for testing.
        2. Define the test inputs.
        3. Call the function under test.
        4. Extract the generated proof from the result.
        5. Obtain the public key corresponding to the private key.
        6. Assert that the public key can verify the generated proof
        using the input message.

        Expected Outcome:
        The generated proof should be valid and verifiable by the
        corresponding public key.
        """

        # Step 1: Generate a private key for testing.
        private_key = ecdsa.SigningKey.generate(curve=ecdsa.SECP256k1)

        # Step 2: Define the test inputs.
        alpha = b"input message"
        bullet_index = 0
        salt = "salt"
        seed_hash = 'seed_hash'
        revolver_chambers = 6

        # Step 3: Call the function under test to get the result.
        result = generate_beta_and_proof(private_key, alpha, seed_hash, salt, revolver_chambers)

        # Step 4: Extract the generated proof from the result.
        proof = result[1]

        # Step 5: Obtain the public key corresponding to the private key.
        public_key = private_key.get_verifying_key()

        # Step 6: Assert that the public key can verify the generated proof using the input message.
        assert public_key.verify(proof, alpha, hashfunc=hashlib.sha256)


    # Tests that generate_beta_and_proof generates a valid beta.
    def test_generate_beta_and_proof_generates_valid_beta(self):
        """
        Test the function generate_beta_and_proof to ensure
        it correctly generates a valid beta value.

        Steps:
        1. Generate a private key for testing.
        2. Define the test inputs.
        3. Call the function under test.
        4. Extract the generated beta, proof, and derived chamber
        index from the result.
        5. Calculate the expected beta value based on the proof,
        salt, and chamber index.
        6. Assert that the generated beta matches the expected value.

        Expected Outcome:
        The generated beta should match the expected value based on
        the given inputs.
        """

        # Step 1: Generate a private key for testing.
        private_key = ecdsa.SigningKey.generate(curve=ecdsa.SECP256k1)

        # Step 2: Define the test inputs.
        alpha = b"input message"
        bullet_index = 0
        salt = "salt"
        seed_hash = 'seed_hash'
        revolver_chambers = 6

        # Step 3: Call the function under test to get the result.
        result = generate_beta_and_proof(private_key, alpha, seed_hash, salt, revolver_chambers)

        # Step 4: Extract the generated beta, proof, and derived chamber index from the result.
        beta = result[0]
        proof = result[1]
        derived_bullet_index = result[2]

        # Step 5: Calculate the expected beta value based on the proof, salt, and chamber index.
        expected_beta = hashlib.pbkdf2_hmac(
            ALGO, 
            ((seed_hash + salt).encode() + proof),
            salt.encode(), ITERATIONS
        ).hex()

        # Step 6: Assert that the generated beta matches the expected value.
        assert beta == expected_beta


    @patch("hashlib.sha256")
    def test_generate_beta_and_proof_derives_valid_bullet_index(self, mock_sha256): 
        """
        Test the function generate_beta_and_proof to
        ensure it correctly derives the chamber index.

        This test focuses on the derived chamber index calculation.
        To ensure consistency and repeatability,
        non-deterministic parts of the function are mocked, such as the
        signing process and the hashing function.

        Steps:
        1. Generate a private key for testing.
        2. Mock the sign method of the private key to always 
        return a fixed proof value.
        3. Mock the hashlib.sha256 function to return a
        deterministic hash value.
        4. Call the function under test.
        5. Calculate the expected beta value based on the proof, salt, and chamber index.
        6. Assert that the derived chamber index from the function
        matches the expected value.
        """

        # Step 1: Generate a private key for testing.
        private_key = ecdsa.SigningKey.generate(curve=ecdsa.SECP256k1)

        # Step 2: Mock the sign method of the private key to always return a fixed proof value.
        mock_proof = b"mocked_proof_value"
        private_key.sign = MagicMock(return_value=mock_proof)

        # Step 3: Mock the hashlib.sha256 function to return a deterministic hash value.
        # This ensures that the hash value is always the same, making the test repeatable.
        mock_hash = MagicMock()
        mock_hash.hexdigest.return_value = '0404040404040404040404040404040404040404040404040404040404040404'  # This will make the expected chamber index 4
        mock_sha256.return_value = mock_hash

        # Define the test inputs.
        alpha = b"input message"
        bullet_index = 1
        salt = "salt"
        seed_hash = "seed_hash"
        revolver_chambers = 7

        # Step 4: Call the function under test.
        beta, proof, derived_bullet_index = generate_beta_and_proof(private_key, alpha, seed_hash, salt, revolver_chambers)

        # Step 5: Calculate the expected beta value based on the proof, salt, and chamber index.
        expected_beta = hashlib.pbkdf2_hmac(
            ALGO, 
            ((seed_hash + salt).encode() + proof),
            salt.encode(), ITERATIONS
        ).hex()

        expected_bullet_index = int(beta, 16) % revolver_chambers

        # Step 6: Assert that the derived chamber index from the function matches the expected value.
        assert derived_bullet_index == expected_bullet_index


    def test_generate_beta_and_proof_raises_verification_error(self):
        """
        Test the function generate_beta_and_proof to ensure
        it raises a VerificationError when there's a failure in
        generating a proof.

        This test focuses on the exception handling mechanism of
        the function.
        The signing process is mocked to raise an exception,
        simulating a failure in the proof generation process.

        Steps:
        1. Generate a private key for testing.
        2. Mock the sign method of the private key to raise a
           VerificationError.
        3. Call the function under test within a pytest.raises
           context to check for the expected VerificationError.
        """
        # Step 1: Generate a private key for testing.
        private_key = ecdsa.SigningKey.generate()
        alpha = b"input message"
        bullet_index = 0
        salt = "salt"
        seed_hash = 'seed_hash'
        revolver_chambers = 6

        # Step 2: Mock the sign method of the private key to raise a VerificationError.
        private_key.sign = MagicMock(side_effect=VerificationError("Mocked signing failure"))

        # Step 3: Call the function under test within a pytest.raises context to check for the expected VerificationError.
        with pytest.raises(VerificationError):
            generate_beta_and_proof(private_key, alpha, seed_hash, salt, revolver_chambers)



    def test_generate_beta_and_proof_handles_large_values(self):
        """
        Test the function generate_beta_and_proof to
        ensure it can handle very large values for bullet_index
        and revolver_size without any issues.

        This test focuses on the function's ability to handle and
        process extremely large input values. It checks if the
        function returns the expected output format and types when
        provided with large values.

        Steps:
        1. Generate a private key for testing.
        2. Define very large values for bullet_index and revolver_size.
        3. Call the function under test with the large values.
        4. Check the type and structure of the returned result to ensure
           it matches the expected format.
        """
        # Step 1: Generate a private key for testing.
        private_key = ecdsa.SigningKey.generate()
        alpha = b"input message"

        # Step 2: Define very large values for bullet_index and revolver_size.
        bullet_index = 10000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000
        salt = "salt"
        seed_hash = 'seed_hash'
        revolver_chambers = 10000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000

        # Step 3: Call the function under test with the large values.
        result = generate_beta_and_proof(private_key, alpha, seed_hash, salt, revolver_chambers)

        # Step 4: Check the type and structure of the returned result to ensure it matches the expected format.
        assert isinstance(result, tuple)
        assert len(result) == 3
        assert isinstance(result[0], str)
        assert isinstance(result[1], bytes)
        assert isinstance(result[2], int)


    def test_generate_beta_and_proof_handles_empty_values(self):
        """
        Test the function generate_beta_and_proof to ensure it raises
        a VerificationError when provided with empty values for alpha and salt.

        This test focuses on the function's ability to handle and validate empty
        input values for alpha and salt. It checks if the function raises the 
        expected VerificationError when provided with empty values.

        Steps:
        1. Generate a private key for testing.
        2. Define empty values for alpha and salt.
        3. Call the function under test within a pytest.raises context to check
        for the expected VerificationError.
        """

        # Step 1: Generate a private key for testing.
        private_key = ecdsa.SigningKey.generate()

        # Step 2: Define empty values.
        alpha = b""
        bullet_index = 0
        salt = ""
        seed_hash = ''
        revolver_chambers = 2

        # Step 3: Call the function under test within a pytest.raises context to check for the expected VerificationError.
        with pytest.raises(VerificationError):
            generate_beta_and_proof(private_key, alpha, seed_hash, salt, revolver_chambers)


    def test_generate_beta_and_proof_handles_negative_values(self):
        """
        Test the function generate_beta_and_proof to ensure it raises
        a VerificationError when provided with negative values for bullet_index
        and revolver_size.

        This test focuses on the function's ability to handle and validate negative
        input values for bullet_index and revolver_size. It checks if the function 
        raises the expected VerificationError when provided with negative values.

        Steps:
        1. Generate a private key for testing.
        2. Define negative values for bullet_index and revolver_size.
        3. Call the function under test within a pytest.raises context to check
        for the expected VerificationError.
        """

        # Step 1: Generate a private key for testing.
        private_key = ecdsa.SigningKey.generate()
        alpha = b"input message"
        bullet_index = -1
        salt = "salt"
        seed_hash = "seed_hash"
        revolver_chambers = -6

        # Step 3: Call the function under test within a pytest.raises context to check for the expected VerificationError.
        with pytest.raises(VerificationError):
            generate_beta_and_proof(private_key, alpha, seed_hash, salt, revolver_chambers)


    # Tests that generate_beta_and_proof handles non-integer values of bullet_index and revolver_size.
    def test_generate_beta_and_proof_handles_non_integer_values(self):
        """
        Test the function generate_beta_and_proof to ensure it raises
        a VerificationError when provided with non-integer values for bullet_index
        and revolver_size.

        This test focuses on the function's ability to handle and validate non-integer
        input values for bullet_index and revolver_size. It checks if the function 
        raises the expected VerificationError when provided with non-integer values.

        Steps:
        1. Generate a private key for testing.
        2. Define non-integer values for bullet_index and revolver_size.
        3. Call the function under test within a pytest.raises context to check
        for the expected VerificationError.
        """
        private_key = ecdsa.SigningKey.generate()
        alpha = b"input message"
        bullet_index = "0"
        salt = "salt"
        seed_hash = 'seed_hash'
        revolver_chambers = "6"

        with pytest.raises(VerificationError):
            generate_beta_and_proof(private_key, alpha, seed_hash, salt, revolver_chambers)


    # Tests that generate_beta_and_proof handles non-string values of salt by raising a VerificationError.
    def test_generate_beta_and_proof_handles_non_string_salt(self):
        """
        Test the function generate_beta_and_proof to ensure it raises
        a VerificationError when provided with non-string values for salt.

        This test focuses on the function's ability to handle and validate non-string
        input values for salt. It checks if the function raises the expected 
        VerificationError when provided with non-string values for salt.

        Steps:
        1. Generate a private key for testing.
        2. Define non-string values for salt.
        3. Call the function under test within a pytest.raises context to check
        for the expected VerificationError.
        """
        private_key = ecdsa.SigningKey.generate()
        alpha = b"input message"
        bullet_index = 0
        salt = 12345
        seed_hash = 'seed_hash'
        revolver_chambers = 6

        with pytest.raises(VerificationError):
            generate_beta_and_proof(private_key, alpha, seed_hash, salt, revolver_chambers)


    """
    Test the function generate_beta_and_proof to ensure it raises
    a VerificationError when provided with non-bytes values for alpha.

    This test focuses on the function's ability to handle and validate non-bytes
    input values for alpha. It checks if the function raises the expected 
    VerificationError when provided with non-bytes values for alpha.

    Steps:
    1. Generate a private key for testing.
    2. Define a non-bytes value for alpha.
    3. Define other necessary input values.
    4. Call the function under test within a pytest.raises context to check
    for the expected VerificationError.
    """
    def test_generate_beta_and_proof_handles_non_bytes_alpha(self):
        private_key = ecdsa.SigningKey.generate()
        alpha = "input message"
        bullet_index = 0
        salt = "salt"
        seed_hash = 'seed_hash'
        revolver_chambers = 6

        with pytest.raises(VerificationError):
            generate_beta_and_proof(private_key, alpha, seed_hash, salt, revolver_chambers)

    def test_generate_proof_none_key(self):
        with pytest.raises(VerificationError):
            generate_proof(private_key=None, alpha="alpha")

    def test_generate_beta_invalid_prood(self):
        with pytest.raises(ValueError):
            generate_beta("str proof", "salt", "seed")
        with pytest.raises(ValueError):
            generate_beta(b"proof", b"byte salt", "seed")
        with pytest.raises(ValueError):
            generate_beta(b"proof", "salt", b"byte seed")

    @patch("hashlib.pbkdf2_hmac", side_effect=VerificationError)
    def test_generate_beta_and_proof_derives_valid_bullet_index(self, mock_pbkdf2_hmac): 
        with pytest.raises(VerificationError):
            generate_beta(b"proof", "salt", "seed")

    # Tests that generate_beta_and_proof generates a valid beta.
    def test_generate_beta_and_proof_invalid_priv_key(self):
        # Step 1: Generate a private key for testing.
        private_key = ecdsa.SigningKey.generate(curve=ecdsa.SECP256k1)

        # Step 2: Define the test inputs.
        alpha = b"input message"
        bullet_index = 0
        salt = "salt"
        seed_hash = 'seed_hash'
        revolver_chambers = 6

        with pytest.raises(VerificationError):
            generate_beta_and_proof('private_key', alpha, seed_hash, salt, revolver_chambers)