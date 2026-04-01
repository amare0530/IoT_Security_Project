#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Phase 2: Anti-Replay Protection Test
測試 Session-based Nonce 防重放功能
"""

from puf_simulator import AuthenticationEngine


def flip_hex_bits(hex_str: str, bit_positions: list[int]) -> str:
    """Flip selected bit positions in a fixed-width 256-bit hex string."""
    value = int(hex_str, 16)
    for pos in bit_positions:
        value ^= (1 << pos)
    return hex(value)[2:].zfill(64)

def main():
    print('【Phase 2: Anti-Replay Protection - Test】')
    print()

    # Initialize engine
    engine = AuthenticationEngine(threshold=45)

    # Deterministic test vectors:
    # - valid response differs by 8 bits (should pass under threshold=45)
    # - invalid response differs by 96 bits (should fail)
    ideal_response = "0" * 64
    noisy_response_valid = flip_hex_bits(ideal_response, [1, 5, 9, 13, 17, 21, 25, 29])
    noisy_response_invalid = flip_hex_bits(ideal_response, list(range(96)))

    # Test 1: Normal authentication with first nonce
    print('Test 1: First authentication with Nonce #1')
    result1 = engine.verify_session(noisy_response_valid, ideal_response, 'nonce_1')
    print(f'  Result: {result1["reason"]}')
    print(f'  Nonce cached: {result1["nonce_used"] == False and result1["authenticated"]}')
    print()

    # Test 2: Replay attack - same nonce
    print('Test 2: Replay Attack - using same Nonce #1')
    result2 = engine.verify_session(noisy_response_valid, ideal_response, 'nonce_1')
    print(f'  Result: {result2["reason"]}')
    print(f'  Replay detected: {"Replay Detected" in result2["reason"]}')
    print()

    # Test 3: New nonce succeeds
    print('Test 3: New authentication with different Nonce #2')
    result3 = engine.verify_session(noisy_response_valid, ideal_response, 'nonce_2')
    print(f'  Result: {result3["reason"]}')
    print(f'  Nonce cached: {result3["nonce_used"] == False and result3["authenticated"]}')
    print()

    # Test 4: Invalid response fails
    print('Test 4: Invalid response with new Nonce #3')
    result4 = engine.verify_session(noisy_response_invalid, ideal_response, 'nonce_3')
    print(f'  Result: {result4["reason"]}')
    print()

    print(f'Nonce cache size: {len(engine.used_nonces)} (expected 2: nonce_1, nonce_2)')

    all_passed = (
        result1["authenticated"] and
        (not result2["authenticated"]) and
        ("Replay Detected" in result2["reason"]) and
        result3["authenticated"] and
        (not result4["authenticated"]) and
        len(engine.used_nonces) == 2
    )
    print(f'{"✅" if all_passed else "❌"} Phase 2 Anti-Replay functionality {"verified" if all_passed else "failed"}!')
    print()
    
    # Detailed output
    print('='*70)
    print('SECURITY ANALYSIS:')
    print('='*70)
    print(f'✅ Test 1 - First auth: {result1["authenticated"]} (expected True)')
    print(f'✅ Test 2 - Replay blocked: {not result2["authenticated"]} (expected True)')
    print(f'✅ Test 3 - New nonce: {result3["authenticated"]} (expected True)')
    print(f'✅ Test 4 - Bad response: {not result4["authenticated"]} (expected True)')
    print()
    print('Security Guarantee:')
    print('- Attackers cannot reuse old (Challenge, Response) pairs')
    print('- Each authentication must use a fresh Nonce')
    print('- Replay attacks are detected and rejected')
    print('='*70)

if __name__ == '__main__':
    main()
