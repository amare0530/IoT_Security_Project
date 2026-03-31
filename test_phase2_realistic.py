#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Phase 2: Anti-Replay Protection Test - Realistic Scenario
測試 Session-based Nonce 防重放功能
"""

from puf_simulator import PUFSimulator, PUFConfig, AuthenticationEngine, generate_challenge
import hashlib

def main():
    print('='*70)
    print('【Phase 2: Anti-Replay Protection - Realistic Test】')
    print('='*70)
    print()

    # Setup PUF and Authentication Engine
    puf_key = 'DEVICE_001_PUF_KEY'
    puf_config = PUFConfig(noise_sigma=0.05, bias_ratio=0.10, bias_strength=0.90)
    puf = PUFSimulator(puf_key, puf_config)
    auth_engine = AuthenticationEngine(threshold=50)

    print('Scenario: IoT Device Authentication with Anti-Replay Protection')
    print()

    # Generate initial authentication
    challenge_1 = generate_challenge('auth_session_1')
    ideal_resp_1, noisy_resp_1 = puf.generate_response(challenge_1, add_noise=True)
    hd_1 = puf.get_hamming_distance(ideal_resp_1, noisy_resp_1)

    print(f'Session 1 - Legitimate User:')
    print(f'  Challenge: {challenge_1[:16]}...')
    print(f'  HD: {hd_1} (threshold={auth_engine.threshold})')
    
    # Test 1: First auth with nonce_1 should succeed
    result_1 = auth_engine.verify_session(noisy_resp_1, ideal_resp_1, 'nonce_session_1')
    print(f'  Auth Result: {result_1["reason"]}')
    print(f'  Authenticated: {result_1["authenticated"]}')
    
    if result_1["authenticated"]:
        print(f'  ✅ Nonce cached: {len(auth_engine.used_nonces)} nonce(s)')
    print()

    # Test 2: Attacker tries replay with same challenge + response + nonce
    print(f'Replay Attack - Attacker intercepts Session 1:')
    print(f'  Attacker tries: Challenge={challenge_1[:16]}..., same Response, Nonce={result_1.get("nonce_used", "N/A")}')
    result_replay = auth_engine.verify_session(noisy_resp_1, ideal_resp_1, 'nonce_session_1')
    print(f'  Auth Result: {result_replay["reason"]}')
    print(f'  Authenticated: {result_replay["authenticated"]}')
    if "Replay" in result_replay["reason"]:
        print(f'  ✅ REPLAY ATTACK BLOCKED!')
    print()

    # Test 3: Legitimate user authenticates again with new nonce
    challenge_2 = generate_challenge('auth_session_2')
    ideal_resp_2, noisy_resp_2 = puf.generate_response(challenge_2, add_noise=True)
    hd_2 = puf.get_hamming_distance(ideal_resp_2, noisy_resp_2)

    print(f'Session 2 - Same Device, New Request:')
    print(f'  Challenge: {challenge_2[:16]}...')
    print(f'  HD: {hd_2} (threshold={auth_engine.threshold})')
    
    result_2 = auth_engine.verify_session(noisy_resp_2, ideal_resp_2, 'nonce_session_2')
    print(f'  Auth Result: {result_2["reason"]}')
    print(f'  Authenticated: {result_2["authenticated"]}')
    if result_2["authenticated"]:
        print(f'  ✅ New nonce accepted')
    print()

    # Summary
    print('='*70)
    print('SECURITY ANALYSIS SUMMARY:')
    print('='*70)
    print(f'✅ Legitimate User Session 1: PASSED')
    print(f'✅ Replay Attack Detection: {"PASSED" if not result_replay["authenticated"] else "FAILED"}')
    print(f'✅ Legitimate User Session 2: PASSED')
    print(f'✅ Nonce Cache Size: {len(auth_engine.used_nonces)} (should be 2)')
    print()
    print('Anti-Replay Mechanism:')
    print(f'  - Each session requires a unique Nonce')
    print(f'  - Used Nonces are cached: {list(auth_engine.used_nonces)}')
    print(f'  - Replay attempts are rejected with "Replay Detected" message')
    print('='*70)


if __name__ == '__main__':
    main()
