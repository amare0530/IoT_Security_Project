import hashlib
import hmac
import secrets

class SimpleVRF:
    """
    教學用 pseudo-VRF（基於 HMAC-SHA256 的 PRF）。
    它具備：
    1. Deterministic (確定性)：同樣的私鑰與 Seed 產出同樣的 C。
    2. Unpredictable (不可預測性)：沒有私鑰的人無法預測下一個 C。
    3. Server-side check (伺服器端可驗證)：伺服器可重算並驗證 C 與摘要。

    注意：
    這不是 RFC 9381 定義的公鑰 VRF（例如 ECVRF），
    proof 也不是可由第三方使用公鑰獨立驗證的證明。
    """
    def __init__(self, server_key):
        self.sk = server_key

    def generate_challenge(self, seed):
        # 產生唯一且隨機的挑戰碼 C
        c = hmac.new(self.sk.encode(), seed.encode(), hashlib.sha256).hexdigest()
        # 產生完整性摘要（server-side check）
        proof = hashlib.sha256((c + self.sk).encode()).hexdigest()[:20]
        return c, proof

    def verify_challenge(self, c, proof, seed):
        # 驗證邏輯：重新計算一次看是否吻合
        expected_c = hmac.new(self.sk.encode(), seed.encode(), hashlib.sha256).hexdigest()
        expected_proof = hashlib.sha256((expected_c + self.sk).encode()).hexdigest()[:20]
        return (c == expected_c) and (proof == expected_proof)

# --- 模擬實作流程 ---
# 1. Server 初始化 (這把私鑰只有 Server 有)
server = SimpleVRF(server_key="FU_JEN_CSIE_SECRET_2026")

# 2. 從 CRP Pool 抽出的種子 (例如編號 001)
db_seed = "CRP_INDEX_001"

# 3. Server 產出挑戰碼 C 與 證明 Proof
c_code, proof_val = server.generate_challenge(db_seed)

print("--- [Server 端作業] ---")
print(f"抽考種子: {db_seed}")
print(f"產生挑戰碼 (C): {c_code}")
print(f"產生驗證證明 (Proof): {proof_val}")
print("\n" + "="*30 + "\n")

# 4. 驗證 (模擬 Server 收到 Node 回傳後的檢查)
is_valid = server.verify_challenge(c_code, proof_val, db_seed)

print("--- [驗證結果] ---")
print(f"此 Challenge 是否由本伺服器發出? {'是 (合法)' if is_valid else '否 (偽造)'}")
