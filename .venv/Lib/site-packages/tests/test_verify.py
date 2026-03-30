import ecdsa
from unittest.mock import patch, MagicMock
import pytest
from vrf_py.VRF import (
    verify
)


class TestVerify:
  """
  This class contains unit tests for the `verify` function in the VRF module.
  """

  # Tests that the function returns True when provided with a valid proof and known valid inputs.
  def test_verify_valid_proof_with_known_inputs(self):
    '''
    Tests the function with a known set of valid inputs and expects a successful verification.
    '''
    public_key = b'''-----BEGIN PUBLIC KEY-----
MFYwEAYHKoZIzj0CAQYFK4EEAAoDQgAED4BkWbqMmS/jxRQKC+xJVF2PeSwEx5g5
WrzeDT8WfdzesmMHFoP5p3yi7KPMsIwa7ZkNRbgvNX4y2wF9f4y9rA==
-----END PUBLIC KEY-----'''
    seed_hash = "76bc35a3dae9c528e44cb9b7c8af1370d252335268ecd4b4d6b79c3b5600cc2d6fd6092cc59e333f12c91e603762e5a4d59feb5d985f9e1feffca0a5bc356ac1"
    salt = "d472f94b879c05d1498c08b7b5e774ace2de515a5f74b1731fde6820c668d28f"
    proof = bytes.fromhex('a60ffb4d2c36655d78e48c41d9887f8b8e29112a5a4f9e001d69a7aeaa72a00ba4acb71eb3d397e8017bd843591c6adc9f4397d92904ac9886e9a1067089efb2')
    bullet_index_hash = 'e9a9cc80a4e3883c16d3a28bf832cd80927d18e26777e058982126addfcd5dcf'
    alpha = b'1694274217300003000060000300006000030000'
    revolver_chambers = 41
    beta = '54f5063e16b06a6dd23727cec6d88d52a9e8f8a84b5f8c4cf1c94035b8316b3d'

    proof_validity, derived_bullet_index_hash = verify(public_key,
                                                       seed_hash,
                                                       salt,
                                                       proof,
                                                       bullet_index_hash,
                                                       alpha,
                                                       revolver_chambers,
                                                       beta)

    assert proof_validity == True
    assert derived_bullet_index_hash == bullet_index_hash


  # Tests that the function returns True when provided with a valid proof and a different set of valid inputs.
  def test_verify_valid_proof_with_different_inputs_same_pub_key(self):
    '''
    Tests the function with a different set of valid inputs but the same public key.
    '''
    public_key = b'''-----BEGIN PUBLIC KEY-----
MFYwEAYHKoZIzj0CAQYFK4EEAAoDQgAED4BkWbqMmS/jxRQKC+xJVF2PeSwEx5g5
WrzeDT8WfdzesmMHFoP5p3yi7KPMsIwa7ZkNRbgvNX4y2wF9f4y9rA==
-----END PUBLIC KEY-----'''
    seed_hash = "37dba05d813d44d52e6b6b9cf402e9b5948ef4e78f312647352016baa085bc5f1061b5c65a3e5d02f60b74df3e27e3eec0e9e09675b45751766fab1687b57593"
    salt = "bca580eeb2bc0605dc24d02d320f482e6293f86003aacfd2c23cf55c86b3b49e"
    proof = bytes.fromhex('bc738f603df0cf25a880c5c709e46346852ebc2f62a583474e0a52b7b4518bd75b51b3fcfe50c4a44768d0a8b15addde25780ef832695935d3624b0327504f0c')
    bullet_index_hash = '16a4abe5d7cfce33c117f09b836cab75e51824c954b61d159f9a391a1c4613b9'
    alpha = b'1694274772300003000060000300006000030000300003000030000'
    revolver_chambers = 22
    beta = '0aeb74b5b2c11a8f59b31034e198986d680128bb07c39801e1c77925af0f34bd'

    proof_validity, derived_bullet_index_hash = verify(public_key,
                                                       seed_hash,
                                                       salt,
                                                       proof,
                                                       bullet_index_hash,
                                                       alpha,
                                                       revolver_chambers,
                                                       beta)

    assert proof_validity == True
    assert derived_bullet_index_hash == bullet_index_hash


  def test_verify_valid_proof_with_different_public_key(self):
    '''
    Tests the function with a different valid public key.
    '''
    public_key = b'''-----BEGIN PUBLIC KEY-----
MFYwEAYHKoZIzj0CAQYFK4EEAAoDQgAE1DJ2RmUmTwg07t9w83Q5m4vNhqDqu2Xe
c0S1sJX01clxnSv3PsPI7g9Lujsc5+87q6NJ05eljd8R6jMRJV7nlQ==
-----END PUBLIC KEY-----'''
    seed_hash = "fdb3b943e81b4a7d312515ff871cf1638d12679a0b855bdaaa6f7c8263f574e60e6a87a0c079d27ccea50ba1ba0d632273bc01232c3ec685d63b07590733e039"
    salt = "96639d08641417aebe1b68912ab08c10da412bf57c126ded4adaeec0f5230d86"
    proof = bytes.fromhex('f58c633a2a947ed31c6143f5d73c6bec82e22081ba5536c52328fe8f93b320c2c5209de1f5dc0d6b0ad28b28fe712fcc88264e06ab14736f2bfc67106ed9b46d')
    bullet_index_hash = 'f06b63ab52e55bd1eb19824eca3882567a867a4166d6472e87dc4411f7aeeb3b'
    alpha = b'1694274952300003000060000300006000030000'
    revolver_chambers = 41
    beta = '91848bd9f29ce163cdac8999ec7278d7bc19c9fbe808e5184614588c298109a4'

    proof_validity, derived_bullet_index_hash = verify(public_key,
                                                       seed_hash,
                                                       salt,
                                                       proof,
                                                       bullet_index_hash,
                                                       alpha,
                                                       revolver_chambers,
                                                       beta)

    assert proof_validity == True
    assert derived_bullet_index_hash == bullet_index_hash


  def test_valid_verify_with_min_chambers(self):
    '''
    Tests the function with the minimum number of revolver chambers.
    '''
    public_key = b'''-----BEGIN PUBLIC KEY-----
MFYwEAYHKoZIzj0CAQYFK4EEAAoDQgAE1DJ2RmUmTwg07t9w83Q5m4vNhqDqu2Xe
c0S1sJX01clxnSv3PsPI7g9Lujsc5+87q6NJ05eljd8R6jMRJV7nlQ==
-----END PUBLIC KEY-----'''
    seed_hash = "a39a775cb04afadbe7eaf95519ddb87d96c6883e341bfe46726692a46f3c96fba05ba619da7d22644feaae7103d2d0159243ec34a8e37e4a40c8dfb6e8d5708b"
    salt = "6ebc24ff40dc186c42d6b7fd71d1d844c1f5cafd2811633d044f5e188a1ba68e"
    proof = bytes.fromhex('8e1677fe5ea4c5a3e4980c92d5774820230c0d2743846888e52f42019001bea05f22739ab3f454c5f42181fc7eb7c9575ad57986c7963e275d00ea2d5e57320a')
    bullet_index_hash = 'afaf2081f389d32c34198693134350ab0373b92f224b5dee7b662e53f1cf558e'
    alpha = b'16942763713000030000'
    revolver_chambers = 2
    beta = '947f71a558be2612dafa457751bf2a9ae13031416df98c3e42f6c72220764492'

    proof_validity, derived_bullet_index_hash = verify(public_key,
                                                       seed_hash,
                                                       salt,
                                                       proof,
                                                       bullet_index_hash,
                                                       alpha,
                                                       revolver_chambers,
                                                       beta)

    assert proof_validity == True
    assert derived_bullet_index_hash == bullet_index_hash


  def test_valid_verify_with_small_chambers(self):
    '''
    Tests the function with a small number of revolver chambers.
    '''
    public_key = b'''-----BEGIN PUBLIC KEY-----
MFYwEAYHKoZIzj0CAQYFK4EEAAoDQgAE1DJ2RmUmTwg07t9w83Q5m4vNhqDqu2Xe
c0S1sJX01clxnSv3PsPI7g9Lujsc5+87q6NJ05eljd8R6jMRJV7nlQ==
-----END PUBLIC KEY-----'''
    seed_hash = "fadfaa2797582565101054fd6859ab3666fd5ea981280726978b241bd47aba23c87c6a37234f9d3ebfff6c16707985ccf21b8f09b8e8608b964efc574dda014a"
    salt = "1232cd7e0920e12ffd22a96f2d2451ca9fb1fe58529fdb9265b6de516d7cd181"
    proof = bytes.fromhex('1ac6de4471e78bb1ef363b34d36d39b6b0989a834110f1e256a0ecc499446e18f1d3466ba037e7f4443ce3cae2eb9179af93da321b9563743c9ebc1ec86ee0d1')
    bullet_index_hash = '810e2393563512d3f794a69710ec5d750fd83920f68135d0916171fb77157657'
    alpha = b'1694276451300003000030000'
    revolver_chambers = 3
    beta = 'e311428f2a46a4f66f57b7e6cb3b7da829eb2eb4f2739105dd693f85d5ae4a13'

    proof_validity, derived_bullet_index_hash = verify(public_key,
                                                       seed_hash,
                                                       salt,
                                                       proof,
                                                       bullet_index_hash,
                                                       alpha,
                                                       revolver_chambers,
                                                       beta)

    assert proof_validity == True
    assert derived_bullet_index_hash == bullet_index_hash


  def test_valid_verify_with_same_chambers_and_bets(self):
    '''
    Tests the function with the same number of revolver chambers and bets.
    '''
    public_key = b'''-----BEGIN PUBLIC KEY-----
MFYwEAYHKoZIzj0CAQYFK4EEAAoDQgAE1DJ2RmUmTwg07t9w83Q5m4vNhqDqu2Xe
c0S1sJX01clxnSv3PsPI7g9Lujsc5+87q6NJ05eljd8R6jMRJV7nlQ==
-----END PUBLIC KEY-----'''
    seed_hash = "6d52ffbb859f1d540e9529931ec053de9ffcb7b4c885e759a361d5f0a0c1f3f6677cda1de5b43ab0e56ca337759c86067735609b5bd5e59db5d37a42eb510b82"
    salt = "f371978c5b38a62e43043865b3f114d46af4422042821ecccab5e06fdad66587"
    proof = bytes.fromhex('1fb221216ed9e6c0e03281ded4f6edc51030834696788f24a3639946eed616de97b97d32dcd317acabbbfc759d83316ca6358a1d477b2480cf63d2fc8c6b1f24')
    bullet_index_hash = 'd2d7c65c5e89f56976deddc798f9da9f4f3bdff31a47114c5acc550af351256c'
    alpha = b'1694276581300003000030000'
    revolver_chambers = 3
    beta = 'd7340d5f541358eb77ff7eef968e5db1d68032edb9e39c8c2b6bda6b2f15911d'

    proof_validity, derived_bullet_index_hash = verify(public_key,
                                                       seed_hash,
                                                       salt,
                                                       proof,
                                                       bullet_index_hash,
                                                       alpha,
                                                       revolver_chambers,
                                                       beta)

    assert proof_validity == True
    assert derived_bullet_index_hash == bullet_index_hash

  def test_valid_verify_with_same_chambers_and_diff_bets(self):
    '''
    Tests the function with the same number of revolver chambers but different bets.
    '''
    public_key = b'''-----BEGIN PUBLIC KEY-----
MFYwEAYHKoZIzj0CAQYFK4EEAAoDQgAE1DJ2RmUmTwg07t9w83Q5m4vNhqDqu2Xe
c0S1sJX01clxnSv3PsPI7g9Lujsc5+87q6NJ05eljd8R6jMRJV7nlQ==
-----END PUBLIC KEY-----'''
    seed_hash = "d51683bec03aaa13c3f9ec9eebc6eebec33e8642a483283e0fada0a8f73038435e5a8eb4f09a272f31c034f80114ba9bcdc342720dfaac2af5be0ff46526fef9"
    salt = "9c797ee4a9fb961c95ec1e2fe4ed9dd6209e3f3d1716fea33f1cd9715e310104"
    proof = bytes.fromhex('4a8fba40d6ef41a27d94e6c4ca13cd4dfa7bc9f9a4baadcc3c1854c8817c26269026f21295bf01916aeebaef859cd2c397cdb324a6af77d042e9a8680a960b7f')
    bullet_index_hash = '22b943c3736d5ebbb9e29ac735448f9e384d7fc0229ceec2e19fbbd01da52681'
    alpha = b'1694276755200020004000'
    revolver_chambers = 3
    beta = '0642433d6f7eaa69f3acab82269857f4a6f49a9c83b23452c3c31395df577240'

    proof_validity, derived_bullet_index_hash = verify(public_key,
                                                       seed_hash,
                                                       salt,
                                                       proof,
                                                       bullet_index_hash,
                                                       alpha,
                                                       revolver_chambers,
                                                       beta)

    assert proof_validity == True
    assert derived_bullet_index_hash == bullet_index_hash

  def test_invalid_revolver_size(self):
    '''
    Tests the function where the revolver chambers is incorrect.
    '''
    public_key = b'''-----BEGIN PUBLIC KEY-----
MFYwEAYHKoZIzj0CAQYFK4EEAAoDQgAE1DJ2RmUmTwg07t9w83Q5m4vNhqDqu2Xe
c0S1sJX01clxnSv3PsPI7g9Lujsc5+87q6NJ05eljd8R6jMRJV7nlQ==
-----END PUBLIC KEY-----'''
    seed_hash = "fdb3b943e81b4a7d312515ff871cf1638d12679a0b855bdaaa6f7c8263f574e60e6a87a0c079d27ccea50ba1ba0d632273bc01232c3ec685d63b07590733e039"
    salt = "96639d08641417aebe1b68912ab08c10da412bf57c126ded4adaeec0f5230d86"
    proof = bytes.fromhex('f58c633a2a947ed31c6143f5d73c6bec82e22081ba5536c52328fe8f93b320c2c5209de1f5dc0d6b0ad28b28fe712fcc88264e06ab14736f2bfc67106ed9b46d')
    bullet_index_hash = None
    alpha = b'1694274952300003000060000300006000030000'
    revolver_chambers = 42 # Wrong, correct value is 41
    beta = '91848bd9f29ce163cdac8999ec7278d7bc19c9fbe808e5184614588c298109a4'

    proof_validity, derived_bullet_index_hash = verify(public_key,
                                                       seed_hash,
                                                       salt,
                                                       proof,
                                                       bullet_index_hash,
                                                       alpha,
                                                       revolver_chambers,
                                                       beta)

    assert proof_validity == False
    assert derived_bullet_index_hash == bullet_index_hash


  def test_invalid_alpha(self):
    '''
    Tests the function where the alpha is incorrect.
    '''
    public_key = b'''-----BEGIN PUBLIC KEY-----
MFYwEAYHKoZIzj0CAQYFK4EEAAoDQgAE1DJ2RmUmTwg07t9w83Q5m4vNhqDqu2Xe
c0S1sJX01clxnSv3PsPI7g9Lujsc5+87q6NJ05eljd8R6jMRJV7nlQ==
-----END PUBLIC KEY-----'''
    seed_hash = "fdb3b943e81b4a7d312515ff871cf1638d12679a0b855bdaaa6f7c8263f574e60e6a87a0c079d27ccea50ba1ba0d632273bc01232c3ec685d63b07590733e039"
    salt = "96639d08641417aebe1b68912ab08c10da412bf57c126ded4adaeec0f5230d86"
    proof = bytes.fromhex('f58c633a2a947ed31c6143f5d73c6bec82e22081ba5536c52328fe8f93b320c2c5209de1f5dc0d6b0ad28b28fe712fcc88264e06ab14736f2bfc67106ed9b46d')
    bullet_index_hash = None
    alpha = b'16942749523000030000600003000060000' # Append '30000' for real value.
    revolver_chambers = 41
    beta = '947f71a558be2612dafa457751bf2a9ae13031416df98c3e42f6c72220764492'

    proof_validity, derived_bullet_index_hash = verify(public_key,
                                                       seed_hash,
                                                       salt,
                                                       proof,
                                                       bullet_index_hash,
                                                       alpha,
                                                       revolver_chambers,
                                                       beta)

    assert proof_validity == False
    assert derived_bullet_index_hash == bullet_index_hash


  def test_invalid_proof(self):
    '''
    Tests the function where the proof is incorrect.
    '''
    public_key = b'''-----BEGIN PUBLIC KEY-----
MFYwEAYHKoZIzj0CAQYFK4EEAAoDQgAE1DJ2RmUmTwg07t9w83Q5m4vNhqDqu2Xe
c0S1sJX01clxnSv3PsPI7g9Lujsc5+87q6NJ05eljd8R6jMRJV7nlQ==
-----END PUBLIC KEY-----'''
    seed_hash = "fdb3b943e81b4a7d312515ff871cf1638d12679a0b855bdaaa6f7c8263f574e60e6a87a0c079d27ccea50ba1ba0d632273bc01232c3ec685d63b07590733e039"
    salt = "96639d08641417aebe1b68912ab08c10da412bf57c126ded4adaeec0f5230d86"
    # real_proof = bytes.fromhex('f58c633a2a947ed31c6143f5d73c6bec82e22081ba5536c52328fe8f93b320c2c5209de1f5dc0d6b0ad28b28fe712fcc88264e06ab14736f2bfc67106ed9b46d')
    proof = bytes.fromhex('f68c633a2a947ed31c6143f5d73c6bec82e22081ba5536c52328fe8f93b320c2c5209de1f5dc0d6b0ad28b28fe712fcc88264e06ab14736f2bfc67106ed9b46d')
    bullet_index_hash = None
    alpha = b'1694274952300003000060000300006000030000'
    revolver_chambers = 41
    beta = '947f71a558be2612dafa457751bf2a9ae13031416df98c3e42f6c72220764492'

    proof_validity, derived_bullet_index_hash = verify(public_key,
                                                       seed_hash,
                                                       salt,
                                                       proof,
                                                       bullet_index_hash,
                                                       alpha,
                                                       revolver_chambers,
                                                       beta)

    assert proof_validity == False
    assert derived_bullet_index_hash == bullet_index_hash


  def test_invalid_salt(self):
    '''
    Tests the function where the salt is incorrect.
    '''
    public_key = b'''-----BEGIN PUBLIC KEY-----
MFYwEAYHKoZIzj0CAQYFK4EEAAoDQgAE1DJ2RmUmTwg07t9w83Q5m4vNhqDqu2Xe
c0S1sJX01clxnSv3PsPI7g9Lujsc5+87q6NJ05eljd8R6jMRJV7nlQ==
-----END PUBLIC KEY-----'''
    seed_hash = "fdb3b943e81b4a7d312515ff871cf1638d12679a0b855bdaaa6f7c8263f574e60e6a87a0c079d27ccea50ba1ba0d632273bc01232c3ec685d63b07590733e039"
    # real_salt = "96639d08641417aebe1b68912ab08c10da412bf57c126ded4adaeec0f5230d86"
    salt = "86639d08641417aebe1b68912ab08c10da412bf57c126ded4adaeec0f5230d86"
    proof = bytes.fromhex('f58c633a2a947ed31c6143f5d73c6bec82e22081ba5536c52328fe8f93b320c2c5209de1f5dc0d6b0ad28b28fe712fcc88264e06ab14736f2bfc67106ed9b46d')
    bullet_index_hash = None
    alpha = b'1694274952300003000060000300006000030000'
    revolver_chambers = 41
    beta = '947f71a558be2612dafa457751bf2a9ae13031416df98c3e42f6c72220764492'

    proof_validity, derived_bullet_index_hash = verify(public_key,
                                                       seed_hash,
                                                       salt,
                                                       proof,
                                                       bullet_index_hash,
                                                       alpha,
                                                       revolver_chambers,
                                                       beta)

    assert proof_validity == False
    assert derived_bullet_index_hash == bullet_index_hash


  def test_invalid_seed_hash(self):
    '''
    Tests the function where the seed hash is incorrect.
    '''
    public_key = b'''-----BEGIN PUBLIC KEY-----
MFYwEAYHKoZIzj0CAQYFK4EEAAoDQgAE1DJ2RmUmTwg07t9w83Q5m4vNhqDqu2Xe
c0S1sJX01clxnSv3PsPI7g9Lujsc5+87q6NJ05eljd8R6jMRJV7nlQ==
-----END PUBLIC KEY-----'''
    # real_seed_hash = "fdb3b943e81b4a7d312515ff871cf1638d12679a0b855bdaaa6f7c8263f574e60e6a87a0c079d27ccea50ba1ba0d632273bc01232c3ec685d63b07590733e039"
    seed_hash = "fdb4b943e81b4a7d312515ff871cf1638d12679a0b855bdaaa6f7c8263f574e60e6a87a0c079d27ccea50ba1ba0d632273bc01232c3ec685d63b07590733e039"
    salt = "96639d08641417aebe1b68912ab08c10da412bf57c126ded4adaeec0f5230d86"
    proof = bytes.fromhex('f58c633a2a947ed31c6143f5d73c6bec82e22081ba5536c52328fe8f93b320c2c5209de1f5dc0d6b0ad28b28fe712fcc88264e06ab14736f2bfc67106ed9b46d')
    bullet_index_hash = None
    alpha = b'1694274952300003000060000300006000030000'
    revolver_chambers = 41
    beta = '3c120f9842793e5d8ac3e2a4b61b2118059aa0343004ed934bbc6b0ff9834fe1'

    proof_validity, derived_bullet_index_hash = verify(public_key,
                                                       seed_hash,
                                                       salt,
                                                       proof,
                                                       bullet_index_hash,
                                                       alpha,
                                                       revolver_chambers,
                                                       beta)

    assert proof_validity == False
    assert derived_bullet_index_hash == bullet_index_hash

  
  def test_invalid_pub_key(self):
    '''
    Tests the function where the public key is incorrect.
    '''
#     real_public_key = b'''-----BEGIN PUBLIC KEY-----
# MFYwEAYHKoZIzj0CAQYFK4EEAAoDQgAE1DJ2RmUmTwg07t9w83Q5m4vNhqDqu2Xe
# c0S1sJX01clxnSv3PsPI7g9Lujsc5+87q6NJ05eljd8R6jMRJV7nlQ==
# -----END PUBLIC KEY-----'''
    public_key = b'''-----BEGIN PUBLIC KEY-----
MFYwEAYHKoZIzj0CAQYFK4EEAAoDQgAED4BkWbqMmS/jxRQKC+xJVF2PeSwEx5g5
WrzeDT8WfdzesmMHFoP5p3yi7KPMsIwa7ZkNRbgvNX4y2wF9f4y9rA==
-----END PUBLIC KEY-----'''
    seed_hash = "fdb3b943e81b4a7d312515ff871cf1638d12679a0b855bdaaa6f7c8263f574e60e6a87a0c079d27ccea50ba1ba0d632273bc01232c3ec685d63b07590733e039"
    salt = "96639d08641417aebe1b68912ab08c10da412bf57c126ded4adaeec0f5230d86"
    proof = bytes.fromhex('f58c633a2a947ed31c6143f5d73c6bec82e22081ba5536c52328fe8f93b320c2c5209de1f5dc0d6b0ad28b28fe712fcc88264e06ab14736f2bfc67106ed9b46d')
    bullet_index_hash = None
    alpha = b'1694274952300003000060000300006000030000'
    revolver_chambers = 41
    beta = '947f71a558be2612dafa457751bf2a9ae13031416df98c3e42f6c72220764492'

    proof_validity, derived_bullet_index_hash = verify(public_key,
                                                       seed_hash,
                                                       salt,
                                                       proof,
                                                       bullet_index_hash,
                                                       alpha,
                                                       revolver_chambers,
                                                       beta)

    assert proof_validity == False
    assert derived_bullet_index_hash == bullet_index_hash


  @patch('ecdsa.keys.VerifyingKey.verify', side_effect=InterruptedError)
  def test_vk_verify_exception(self, mocked_sig):
    public_key = b'''-----BEGIN PUBLIC KEY-----
MFYwEAYHKoZIzj0CAQYFK4EEAAoDQgAE1DJ2RmUmTwg07t9w83Q5m4vNhqDqu2Xe
c0S1sJX01clxnSv3PsPI7g9Lujsc5+87q6NJ05eljd8R6jMRJV7nlQ==
-----END PUBLIC KEY-----'''
    # real_seed_hash = "fdb3b943e81b4a7d312515ff871cf1638d12679a0b855bdaaa6f7c8263f574e60e6a87a0c079d27ccea50ba1ba0d632273bc01232c3ec685d63b07590733e039"
    seed_hash = "fdb4b943e81b4a7d312515ff871cf1638d12679a0b855bdaaa6f7c8263f574e60e6a87a0c079d27ccea50ba1ba0d632273bc01232c3ec685d63b07590733e039"
    salt = "96639d08641417aebe1b68912ab08c10da412bf57c126ded4adaeec0f5230d86"
    proof = bytes.fromhex('f58c633a2a947ed31c6143f5d73c6bec82e22081ba5536c52328fe8f93b320c2c5209de1f5dc0d6b0ad28b28fe712fcc88264e06ab14736f2bfc67106ed9b46d')
    bullet_index_hash = None
    alpha = b'1694274952300003000060000300006000030000'
    revolver_chambers = 41
    beta = '575bf0b4da9be711155c744cd2eafda2bb91c642d355e66a3f20a3ca6b3bd54d'

    proof_validity, derived_bullet_index_hash = verify(public_key,
                                                       seed_hash,
                                                       salt,
                                                       proof,
                                                       bullet_index_hash,
                                                       alpha,
                                                       revolver_chambers,
                                                       beta)
    
    assert proof_validity == False
    assert derived_bullet_index_hash == bullet_index_hash


  @patch('ecdsa.keys.VerifyingKey.verify', side_effect=ValueError)
  def test_vk_verify_exception_value_error(self, mocked_sig):
    public_key = b'''-----BEGIN PUBLIC KEY-----
MFYwEAYHKoZIzj0CAQYFK4EEAAoDQgAE1DJ2RmUmTwg07t9w83Q5m4vNhqDqu2Xe
c0S1sJX01clxnSv3PsPI7g9Lujsc5+87q6NJ05eljd8R6jMRJV7nlQ==
-----END PUBLIC KEY-----'''
    # real_seed_hash = "fdb3b943e81b4a7d312515ff871cf1638d12679a0b855bdaaa6f7c8263f574e60e6a87a0c079d27ccea50ba1ba0d632273bc01232c3ec685d63b07590733e039"
    seed_hash = "fdb4b943e81b4a7d312515ff871cf1638d12679a0b855bdaaa6f7c8263f574e60e6a87a0c079d27ccea50ba1ba0d632273bc01232c3ec685d63b07590733e039"
    salt = "96639d08641417aebe1b68912ab08c10da412bf57c126ded4adaeec0f5230d86"
    proof = bytes.fromhex('f58c633a2a947ed31c6143f5d73c6bec82e22081ba5536c52328fe8f93b320c2c5209de1f5dc0d6b0ad28b28fe712fcc88264e06ab14736f2bfc67106ed9b46d')
    bullet_index_hash = None
    alpha = b'1694274952300003000060000300006000030000'
    revolver_chambers = 41
    beta = '947f71a558be2612dafa457751bf2a9ae13031416df98c3e42f6c72220764492'

    proof_validity, derived_bullet_index_hash = verify(public_key,
                                                       seed_hash,
                                                       salt,
                                                       proof,
                                                       bullet_index_hash,
                                                       alpha,
                                                       revolver_chambers,
                                                       beta)
    
    assert proof_validity == False
    assert derived_bullet_index_hash == bullet_index_hash

  
  @patch('ecdsa.keys.VerifyingKey.verify', return_valud=True)
  def test_happy_path_not_successful(self, mocked_sig):
    public_key = b'''-----BEGIN PUBLIC KEY-----
MFYwEAYHKoZIzj0CAQYFK4EEAAoDQgAE1DJ2RmUmTwg07t9w83Q5m4vNhqDqu2Xe
c0S1sJX01clxnSv3PsPI7g9Lujsc5+87q6NJ05eljd8R6jMRJV7nlQ==
-----END PUBLIC KEY-----'''
    # real_seed_hash = "fdb3b943e81b4a7d312515ff871cf1638d12679a0b855bdaaa6f7c8263f574e60e6a87a0c079d27ccea50ba1ba0d632273bc01232c3ec685d63b07590733e039"
    seed_hash = "fdb4b943e81b4a7d312515ff871cf1638d12679a0b855bdaaa6f7c8263f574e60e6a87a0c079d27ccea50ba1ba0d632273bc01232c3ec685d63b07590733e039"
    salt = "96639d08641417aebe1b68912ab08c10da412bf57c126ded4adaeec0f5230d86"
    proof = bytes.fromhex('f58c633a2a947ed31c6143f5d73c6bec82e22081ba5536c52328fe8f93b320c2c5209de1f5dc0d6b0ad28b28fe712fcc88264e06ab14736f2bfc67106ed9b46d')
    bullet_index_hash = 'FAKE'
    alpha = b'1694274952300003000060000300006000030000'
    revolver_chambers = 41
    beta = '947f71a558be2612dafa457751bf2a9ae13031416df98c3e42f6c72220764492'

    proof_validity, derived_bullet_index_hash = verify(public_key,
                                                       seed_hash,
                                                       salt,
                                                       proof,
                                                       bullet_index_hash,
                                                       alpha,
                                                       revolver_chambers,
                                                       beta)
    
    assert proof_validity == False
    assert derived_bullet_index_hash == None


  def test_invalid_beta(self):
    '''
    Tests the function with the same number of revolver chambers but different bets.
    '''
    public_key = b'''-----BEGIN PUBLIC KEY-----
MFYwEAYHKoZIzj0CAQYFK4EEAAoDQgAE1DJ2RmUmTwg07t9w83Q5m4vNhqDqu2Xe
c0S1sJX01clxnSv3PsPI7g9Lujsc5+87q6NJ05eljd8R6jMRJV7nlQ==
-----END PUBLIC KEY-----'''
    seed_hash = "d51683bec03aaa13c3f9ec9eebc6eebec33e8642a483283e0fada0a8f73038435e5a8eb4f09a272f31c034f80114ba9bcdc342720dfaac2af5be0ff46526fef9"
    salt = "9c797ee4a9fb961c95ec1e2fe4ed9dd6209e3f3d1716fea33f1cd9715e310104"
    proof = bytes.fromhex('4a8fba40d6ef41a27d94e6c4ca13cd4dfa7bc9f9a4baadcc3c1854c8817c26269026f21295bf01916aeebaef859cd2c397cdb324a6af77d042e9a8680a960b7f')
    bullet_index_hash = '22b943c3736d5ebbb9e29ac735448f9e384d7fc0229ceec2e19fbbd01da52681'
    alpha = b'1694276755200020004000'
    revolver_chambers = 3
    # real_beta = '0642433d6f7eaa69f3acab82269857f4a6f49a9c83b23452c3c31395df577240'
    beta = '1234567890'

    proof_validity, derived_bullet_index_hash = verify(public_key,
                                                       seed_hash,
                                                       salt,
                                                       proof,
                                                       bullet_index_hash,
                                                       alpha,
                                                       revolver_chambers,
                                                       beta)

    assert proof_validity == False
    assert derived_bullet_index_hash == None