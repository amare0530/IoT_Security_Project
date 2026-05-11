import numpy as np

from puf.fuzzy_extractor import FuzzyExtractor, _random_noise_success_rate


def test_code_offset_reconstructs_key_with_and_without_noise() -> None:
    fe = FuzzyExtractor(bits_needed=16, repetition=11)
    response = np.tile(np.array([0, 1, 1, 0], dtype=np.uint8), 64)
    mask = np.ones_like(response, dtype=np.uint8)
    rng = np.random.default_rng(1234)

    key, helper_data = fe.gen(response, mask, uid="device-001", rng=rng)

    assert fe.rep(response, helper_data) == key

    noisy = response.copy()
    indices = np.array(helper_data["stable_indices"])
    noisy[indices[:: fe.repetition][:8]] ^= 1

    assert fe.rep(noisy, helper_data) == key


def test_uid_does_not_determine_enrollment_key() -> None:
    fe = FuzzyExtractor(bits_needed=16, repetition=11)
    response = np.tile(np.array([1, 0, 0, 1], dtype=np.uint8), 64)
    mask = np.ones_like(response, dtype=np.uint8)

    key_a, _ = fe.gen(
        response, mask, uid="same-device", rng=np.random.default_rng(1)
    )
    key_b, _ = fe.gen(
        response, mask, uid="same-device", rng=np.random.default_rng(2)
    )

    assert key_a != key_b


def test_random_noise_success_rate_reports_probability() -> None:
    fe = FuzzyExtractor(bits_needed=16, repetition=11)
    response = np.tile(np.array([0, 1, 1, 0], dtype=np.uint8), 64)
    mask = np.ones_like(response, dtype=np.uint8)
    key, helper_data = fe.gen(
        response, mask, uid="device-001", rng=np.random.default_rng(1234)
    )

    success_rate = _random_noise_success_rate(
        fe=fe,
        golden=response,
        helper_data=helper_data,
        expected_key=key,
        ber_test=0.05,
        trials=20,
        rng=np.random.default_rng(5678),
    )

    assert 0.0 <= success_rate <= 1.0
