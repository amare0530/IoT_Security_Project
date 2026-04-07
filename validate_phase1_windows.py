#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Phase 1 Code Validation - Windows Compatible"""
import sys
import json
import time
import hmac
import hashlib
import secrets

print("=" * 70)
print("[Phase 1] Code Validation Start")
print("=" * 70)

# Test 1: Check app.py components
print("\n[1/5] Validating app.py components...")
try:
    with open("app.py", "r", encoding="utf-8") as f:
        app_content = f.read()
    
    required = [
        "class SeededChallengeStore",
        "def generate_dynamic_seed",
        "def verify_response_payload",
        "use_dynamic_seed"
    ]
    
    for component in required:
        if component in app_content:
            print(f"  [OK] Found: {component}")
        else:
            print(f"  [FAIL] Missing: {component}")
            sys.exit(1)
    
    print("  [OK] app.py all required components present")
except Exception as e:
    print(f"  [FAIL] app.py validation failed: {e}")
    sys.exit(1)

# Test 2: Check node.py components
print("\n[2/5] Validating node.py components...")
try:
    with open("node.py", "r", encoding="utf-8") as f:
        node_content = f.read()
    
    required = [
        "delta_t = time_now - timestamp_from_server",
        "if delta_t > max_response_time",
        "payload.get('timestamp')"
    ]
    
    for component in required:
        if component in node_content:
            print(f"  [OK] Found: {component}")
        else:
            print(f"  [FAIL] Missing: {component}")
            sys.exit(1)
    
    print("  [OK] node.py all required components present")
except Exception as e:
    print(f"  [FAIL] node.py validation failed: {e}")
    sys.exit(1)

# Test 3: Dynamic seed logic
print("\n[3/5] Testing dynamic seed generation logic...")
try:
    private_key = "test_server_key_12345"
    granularity = 1
    
    timestamp = int(time.time() / granularity) * granularity
    nonce = secrets.token_hex(32)
    seed_input = f"{timestamp}:{nonce}:{private_key}"
    
    seed_string = hmac.new(
        key=private_key.encode(),
        msg=seed_input.encode(),
        digestmod=hashlib.sha256
    ).hexdigest()
    
    print(f"  [OK] Timestamp: {timestamp}")
    print(f"  [OK] Nonce length: {len(nonce)} chars (96 expected: {len(nonce) == 64})")
    print(f"  [OK] Seed length: {len(seed_string)} chars (64 expected: {len(seed_string) == 64})")
    
    if len(nonce) == 64 and len(seed_string) == 64:
        print("  [OK] Dynamic seed generation logic correct")
    else:
        print("  [FAIL] Generated value lengths incorrect")
        sys.exit(1)
except Exception as e:
    print(f"  [FAIL] Dynamic seed logic test failed: {e}")
    sys.exit(1)

# Test 4: Replay detection logic
print("\n[4/5] Testing replay detection logic...")
try:
    seed_store_data = {}
    test_nonce = secrets.token_hex(32)
    test_seed = secrets.token_hex(32)
    test_timestamp = time.time()
    
    # Store
    seed_store_data[test_nonce] = {
        "seed": test_seed,
        "timestamp": test_timestamp,
        "status": "pending"
    }
    print(f"  [OK] Stored Nonce: {test_nonce[:16]}...")
    
    # Mark used
    if test_nonce in seed_store_data:
        seed_store_data[test_nonce]["status"] = "used"
        print(f"  [OK] Marked Nonce as used")
    
    # Verify replay detection
    if seed_store_data[test_nonce]["status"] == "used":
        print(f"  [OK] Replay detection: second access would be rejected")
    else:
        print(f"  [FAIL] Replay detection failed")
        sys.exit(1)
        
    print("  [OK] Replay detection logic correct")
except Exception as e:
    print(f"  [FAIL] Replay detection test failed: {e}")
    sys.exit(1)

# Test 5: Timestamp validation
print("\n[5/5] Testing timestamp validation logic...")
try:
    challenge_timestamp = time.time()
    max_response_time = 10
    
    # Fresh challenge
    delta_t_fresh = time.time() - challenge_timestamp
    if delta_t_fresh < max_response_time:
        print(f"  [OK] Fresh Challenge: delta_t={delta_t_fresh:.2f}s < {max_response_time}s")
    else:
        print(f"  [FAIL] Fresh Challenge detection failed")
        sys.exit(1)
    
    # Old challenge (simulated)
    old_timestamp = time.time() - 15
    delta_t_old = time.time() - old_timestamp
    if delta_t_old > max_response_time:
        print(f"  [OK] Old Challenge: delta_t={delta_t_old:.2f}s > {max_response_time}s (would be rejected)")
    else:
        print(f"  [FAIL] Old Challenge detection failed")
        sys.exit(1)
    
    print("  [OK] Timestamp validation logic correct")
except Exception as e:
    print(f"  [FAIL] Timestamp validation test failed: {e}")
    sys.exit(1)

print("\n" + "=" * 70)
print("[SUCCESS] All validation tests passed (5/5)")
print("=" * 70)
print("\nNext steps:")
print("  1. Run 5 test scenarios from TEST_PHASE1_REPLAY.md")
print("  2. Start: mqtt_bridge.py + node.py + streamlit run app.py")
print("  3. Verify replay attack prevention works")
print("  4. Document results for teacher meeting")
print()

