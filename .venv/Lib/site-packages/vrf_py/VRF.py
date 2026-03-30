import ecdsa.keys
import ecdsa
import hashlib
import secrets
import time

from typing import Tuple, Union
from vrf_py.log import logger
from vrf_py.error import SeedError, VerificationError, InputError

HEX_BASE = 16
SUBSTRING_LENGTH = 8

ALPHA_SALT_ERROR_MSG = 'Alpha or Salt must be of type bytes and str, respectively.'
CHAMBER_REVOLVER_ERROR_MSG = 'Chamber index and revolver size must be of type int.'
PRIVATE_KEY_ERROR_MSG = 'Private key must be an instance of ecdsa.keys.SigningKey.'
PROOF_BETA_ERROR_MSG = 'Failed to generate proof or beta.'


# ITERATIONS = 100000
ITERATIONS = 100
MAX_REVOLVER_SIZE = 50

ALGO : str = 'sha256'


def generate_seed_salt_hash(_algorithm: str = 'sha512') -> Tuple[str, str, str]:
    """
    Generates a random seed, salt, and their hash using the
    PBKDF2 algorithm with a specified hash algorithm and
    number of iterations.

    Args:
        _algorithm (str, optional): A string specifying the
            hash algorithm to use. The default value is 'sha512'.

    Returns:
        tuple: A tuple containing the generated seed, its hash, and the salt.
    """
    if _algorithm not in hashlib.algorithms_guaranteed:
        raise ValueError("Invalid hash algorithm. Supported algorithms are: " + ", ".join(hashlib.algorithms_guaranteed))
    
    seed = secrets.token_hex(16)
    salt = secrets.token_hex(32)
    seed_hash = hashlib.pbkdf2_hmac(
        _algorithm,
        seed.encode(),
        salt.encode(),
        ITERATIONS
    ).hex()
    return seed, seed_hash, salt


def generate_proof(private_key: ecdsa.keys.SigningKey, alpha: bytes) -> bytes:
    """
    Generate a proof using a private key and input message.

    Args:
        private_key (ecdsa.keys.SigningKey): The private key for signing.
        alpha (bytes): The input message.

    Returns:
        bytes: The generated proof.
    """
    if not alpha:
        raise VerificationError('Alpha cannot be empty.')
    if private_key is None:
        raise VerificationError('Private key cannot be None.')

    try:
        return private_key.sign(alpha, hashfunc=hashlib.sha256)
    except Exception as e:
        raise VerificationError('Failed to generate proof.') from e


def generate_beta(proof: bytes, salt: str, seed_hash: str) -> str:
    """
    Generates a beta value using the proof, salt, and seed hash.

    Args:
        proof (bytes): The proof of the random value.
        salt (str): The salt value.
        seed_hash (str): The seed hash value.

    Returns:
        str: The generated beta value as a hexadecimal string.

    Raises:
        VerificationError: If failed to generate beta.

    Example:
        proof = b"proof"
        salt = "salt"
        seed_hash = "seed_hash"
        beta = generate_beta(proof, salt, seed_hash)
        print(beta) # Output: "5eb56d677d7192313903f2c88bb83037f8373b989e3ecfab29112a269b69ddaf"
    """
    if not isinstance(proof, bytes):
        raise ValueError("proof must be a bytes object")
    if not isinstance(salt, str):
        raise ValueError("salt must be a string")
    if not isinstance(seed_hash, str):
        raise ValueError("seed_hash must be a string")

    try:
        beta = hashlib.pbkdf2_hmac(
            ALGO,
            ((seed_hash + salt).encode() + proof),
            salt.encode(),
            ITERATIONS
        ).hex()
        return beta
    except Exception as e:
        raise VerificationError('Failed to generate beta.') from e


def generate_beta_and_proof(
    private_key: ecdsa.keys.SigningKey, alpha: bytes,
    seed_hash: str, salt: str, revolver_chambers: int
) -> Tuple[str, bytes, int]:
    """
    Generate a random value and its proof based on the provided parameters.

    Args:
        private_key (ecdsa.keys.SigningKey): The private key for signing.
        alpha (bytes): A game-specific parameter.
        seed_hash (bytes): Hashed value of the seed.
        salt (str): A random string to ensure uniqueness of the hash.
        revolver_chambers (int): The size of the revolver.

    Returns:
        tuple: A tuple containing:
            - beta (str): A deterministic, unpredictable value derived
                          from the seed_hash, salt, and proof.
            - proof (bytes): A digital signature generated using the
                             private key and alpha.
            - bullet_index (int): The "loaded chamber" in the game,
                                  derived from the beta value.
    """
    if alpha == "" or salt == b"" or salt == "":
        raise VerificationError('Alpha or Salt cannot be empty.')

    if not isinstance(alpha, bytes) or not isinstance(salt, str) or not isinstance(seed_hash, str):
        raise VerificationError(ALPHA_SALT_ERROR_MSG)

    if not isinstance(private_key, ecdsa.keys.SigningKey):
        raise VerificationError(PRIVATE_KEY_ERROR_MSG)

    if not isinstance(revolver_chambers, int):
        raise VerificationError('Revolver size must be an integer.')

    if revolver_chambers <= 1:
        raise VerificationError('Revolver size must be greater than 1.')

    proof = generate_proof(private_key, alpha)
    beta = generate_beta(proof, salt, seed_hash)
    
    '''
    Converts hexadecimal string (beta) into an int.
    Modulus operation on int.
    '''
    bullet_index = int(beta, 16) % revolver_chambers

    return beta, proof, bullet_index


def new_game(revolver_chambers: int,
             private_key: ecdsa.keys.SigningKey,
             alpha: bytes
) -> Tuple[str, str, str, str, bytes, int, str, bytes]:
    """
    Initialize a new game by generating essential cryptographic
    parameters.

    This function sets up the initial state of the game by generating
    a random seed, its hash, and other cryptographic values. It ensures
    the game's randomness, unpredictability, and verifiability.

    Args:
        revolver_chambers (int): The size of the revolver.
        private_key (ecdsa.keys.SigningKey): The private key for signing.
        alpha (bytes): timestamp + player bets.

    Returns:
        tuple: A tuple containing:
            - seed (str): A randomly generated unique identifier.
            - seed_hash (str): Hashed value of the seed.
            - salt (str): A random string.
            - beta (str): A deterministic, unpredictable value derived from the seed_hash, salt, and proof.
            - proof (bytes): A digital signature generated using the private key and alpha.
            - bullet_index (int): The "loaded chamber" in the game, derived from the beta value.
            - bullet_index_hash (str): A commitment to the initial state of the game.
            - public_key_pem (bytes): The public key in PEM format, extracted from the provided private key.
    """
    if not isinstance(revolver_chambers, int):
        raise InputError("Invalid input. revolver size must be an int.")
    if not (2 <= revolver_chambers <= 50):
        raise InputError("Invalid revolver size. It should be between 2 and 50.")

    seed, seed_hash, salt = generate_seed_salt_hash()
    
    beta, proof, bullet_index = generate_beta_and_proof(
        private_key, alpha, seed_hash, salt, revolver_chambers
    )

    bullet_index_hash = hashlib.pbkdf2_hmac(
        ALGO,
        (str(bullet_index) + salt + seed_hash).encode(),
        salt.encode(),
        ITERATIONS
    ).hex()

    public_key_pem = private_key.verifying_key.to_pem()

    return seed, seed_hash, salt, beta, proof, bullet_index, bullet_index_hash, public_key_pem


def verify(public_key: bytes, seed_hash: str, salt: str,
           proof: bytes, bullet_index_hash: str, alpha: bytes,
           revolver_chambers: int, beta: str) -> bool:
    """
    Verify the integrity of the game using the information published at the end of
    the game and the information published at the beginning of the game.

    This function checks the validity of a provided proof
    using a public key and ensures that the derived bullet
    index hash matches the provided hash. It ensures that the
    game's outcome has not been tampered with and is verifiable.

    Args:
        public_key (bytes): The public key in PEM format.
        seed_hash (str): The hash of the randomly generated seed.
        salt (str): The randomly generated salt used for hashing.
        proof (bytes): The generated proof for the random number.
        bullet_index_hash (str): The hash of the bullet index.
        alpha (bytes): The input message to the VRF.
        revolver_chambers (int): The number of chambers in the revolver.
        beta (str): The randomly generated number in hex format.

    Returns:
       Union[Tuple[bool, None], Tuple[bool, str]]:
            - (proof_validity (bool), derived_bullet_index_hash (str)): A tuple
                containing the validity of the proof and the derived bullet
                index hash if all verification steps pass.
    """
    try:
        # Verify the proof using the public key and alpha
        vk = ecdsa.VerifyingKey.from_pem(public_key)
        vk.verify(proof, alpha, hashfunc=hashlib.sha256)

        # Verify the beta value by generating it from the proof, salt, and seed_hash
        derived_beta = generate_beta(proof, salt, seed_hash)

        if derived_beta != beta:
            logger.error("Beta value verification failed.")
            return False, None

        # Get determinisitc beta, get bullet index, get hash of index.
        bullet_index = int(beta, 16) % revolver_chambers
        derived_bullet_index_hash = hashlib.pbkdf2_hmac(
            ALGO,
            (str(bullet_index) + salt + seed_hash).encode(),
            salt.encode(),
            ITERATIONS
        ).hex()

        if derived_bullet_index_hash != bullet_index_hash:
            logger.error("Bullet index verification failed.")
            return False, None

        return True, derived_bullet_index_hash
    except (ecdsa.keys.BadSignatureError, ecdsa.errors.MalformedPointError, ValueError) as error:
        logger.error(f"Verification failed: {error}")
        return False, None
    except Exception as error:
        logger.error(f"Verification failed: {error}")
        return False, None


def example_run():
    revolver_chambers = 2
    bets = [30000, 30000, 60000, 30000, 60000]
    bets = [30000, 30000]

    sk = ecdsa.SigningKey.generate(curve=ecdsa.SECP256k1)
    logger.info(f'Generated a new secret key.\n')
    # while True:
    #     import pdb;pdb.set_trace()
    # revolver_chambers += 1
    # bets.append(30000)
    logger.info(f'Revolver Size): {revolver_chambers}\n')
    logger.info(f'Bets): {bets}\n')

    timestamp = str(int(time.time()))
    alpha_raw = (timestamp + ''.join(map(str, bets)))
    alpha = alpha_raw.encode()
    logger.info(f'Alpha_Raw (Timestampe + Bets): {alpha_raw}')
    logger.info(f'Alpha (Input Message): {alpha}\n')

    # sk = ecdsa.SigningKey.generate(curve=ecdsa.SECP256k1)
    # logger.info(f'Generated a new secret key.\n')
    
    seed, seed_hash, salt, beta, proof, bullet_index, bullet_index_hash, public_key_pem = new_game(revolver_chambers, sk, alpha)
    logger.info(f"Seed: {seed}")
    logger.info(f"Seed Hash: {seed_hash}")
    logger.info(f"Salt: {salt}")
    logger.info(f'Beta: {beta}')
    logger.info(f'Proof: {proof.hex()}')
    logger.info(f'bullet_index: {bullet_index}')
    logger.info(f"bullet_index_hash: {bullet_index_hash}")
    logger.info(f'Public Key: {public_key_pem.decode()}\n')

    import pdb;pdb.set_trace()
    
    proof_validity, derived_bullet_index_hash = verify(public_key_pem, seed_hash, salt, proof, bullet_index_hash, alpha, revolver_chambers, beta)
    logger.info(f'Actual Bullet Index Hash: {derived_bullet_index_hash}')
    logger.info(f'Expected Bullet Index Hash: {bullet_index_hash}')
    logger.info(f'Verification Result: {proof_validity}')

if __name__ == '__main__':
    example_run()