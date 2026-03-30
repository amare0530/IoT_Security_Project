import ecdsa
import pytest
import time
from vrf_py.VRF import (
    new_game
)
from vrf_py.error import SeedError, VerificationError, InputError
from unittest.mock import patch

@pytest.fixture(scope="class")
def game_setup():
    sk = ecdsa.SigningKey.generate(curve=ecdsa.SECP256k1)
    revolver_chambers = 10
    timestamp = str(int(time.time()))
    bets = [30000, 30000, 30000, 30000]
    alpha_raw = (timestamp + ''.join(map(str, bets)))
    alpha = alpha_raw.encode()
    
    return sk, revolver_chambers, alpha

class TestNewGame:
    def test_happy_path_revolver_size_2_bets_1_1(self, game_setup):
        """
        Test the function new_game to ensure it initializes a new game with 
        revolver size 11 and default bets.

        Steps:
        1. Set up the game parameters using the game_setup fixture.
        2. Call the function under test to get the result.
        3. Assert the types of the returned values.

        Expected Outcome:
        The function should return the correct types for each of the game parameters.
        """
        sk, revolver_chambers, alpha = game_setup
        revolver_chambers = 11
        seed, seed_hash, salt, beta, proof, bullet_index, bullet_index_hash, public_key_pem = new_game(revolver_chambers, sk, alpha)
        assert isinstance(seed, str)
        assert isinstance(seed_hash, str)
        assert isinstance(salt, str)
        assert isinstance(beta, str)
        assert isinstance(proof, bytes)
        assert isinstance(bullet_index, int)
        assert isinstance(bullet_index_hash, str)
        assert isinstance(public_key_pem, bytes)

    def test_happy_path_revolver_size_50_bets_1_1_1_1(self, game_setup):
        """
        Test the function new_game to ensure it initializes a new game with 
        revolver size 50 and default bets.

        Steps:
        1. Set up the game parameters using the game_setup fixture.
        2. Call the function under test to get the result.
        3. Assert the types of the returned values and the bullet index.

        Expected Outcome:
        The bullet index should be less than or equal to the revolver size.
        """
        sk, revolver_chambers, alpha = game_setup
        revolver_size = 50
        seed, seed_hash, salt, beta, proof, bullet_index, bullet_index_hash, public_key_pem = new_game(revolver_chambers, sk, alpha)
        assert isinstance(bullet_index_hash, str)
        assert isinstance(salt, str)
        assert isinstance(bullet_index, int)
        assert bullet_index <= revolver_size

    @patch("secrets.token_hex")
    def test_happy_path_revolver_size_10_bets_0_0_0_0_0_0_0_0_0_0(self, mock_token_hex, game_setup):
        """
        Test the function new_game with a mocked secrets.token_hex function 
        to ensure consistent results.

        Steps:
        1. Mock the secrets.token_hex function to return a fixed value.
        2. Set up the game parameters using the game_setup fixture.
        3. Call the function under test to get the result.
        4. Assert the types of the returned values and the bullet index.

        Expected Outcome:
        The bullet index should be less than or equal to the revolver size.
        """
        mock_token_hex.return_value = "abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890"
        sk, revolver_chambers, alpha = game_setup
        revolver_size = 10
        seed, seed_hash, salt, beta, proof, bullet_index, bullet_index_hash, public_key_pem = new_game(revolver_chambers, sk, alpha)
        assert isinstance(bullet_index_hash, str)
        assert isinstance(salt, str)
        assert isinstance(bullet_index, int)
        assert bullet_index <= revolver_size

    def test_edge_case_revolver_size_1_bets_1(self, game_setup):
        """
        Test the function new_game to ensure it raises an InputError when 
        the revolver size is 1.

        Steps:
        1. Set up the game parameters using the game_setup fixture.
        2. Call the function under test and expect an InputError.

        Expected Outcome:
        The function should raise an InputError.
        """
        sk, revolver_chambers, alpha = game_setup
        revolver_chambers = 1
        with pytest.raises(InputError):
            new_game(revolver_chambers, sk, alpha)

    def test_edge_case_revolver_size_51_bets_1_1_1_1(self, game_setup):
        """
        Test the function new_game to ensure it raises an InputError when 
        the revolver size is 51.

        Steps:
        1. Set up the game parameters using the game_setup fixture.
        2. Call the function under test and expect an InputError.

        Expected Outcome:
        The function should raise an InputError.
        """
        sk, revolver_chambers, alpha = game_setup
        revolver_chambers = 51
        with pytest.raises(InputError):
            new_game(revolver_chambers, sk, alpha)

    def test_edge_case_revolver_size_10_alpha_empty(self, game_setup):
        """
        Test the function new_game to ensure it raises a VerificationError 
        when the alpha value is empty.

        Steps:
        1. Set up the game parameters using the game_setup fixture.
        2. Call the function under test and expect a VerificationError.

        Expected Outcome:
        The function should raise a VerificationError.
        """
        sk, revolver_chambers, alpha = game_setup
        alpha = b''
        with pytest.raises(VerificationError):
            new_game(revolver_chambers, sk, alpha)

    def test_invalid_revolver_chambers(self, game_setup):
        sk, revolver_chambers, alpha = game_setup
        revolver_chambers = 'INVALID'
        with pytest.raises(InputError):
            new_game(revolver_chambers, sk, alpha)