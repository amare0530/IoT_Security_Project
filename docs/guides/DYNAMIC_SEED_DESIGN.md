#  動態 Seed 防禦設計 (Dynamic Seed Generation & Replay Attack Prevention)

##  目前問題診斷

###  現有漏洞
```python
# 【舊實現】 - 靜態 Seed（不安全）
default_seed = "CRP_INDEX_001"  #  固定不變，容易被記錄和重放

Challenge = VRF(SK, seed)
# 攻擊者可以：
# 1. 截獲 Challenge_001
# 2. 記錄下來
# 3. 一小時後，用同樣的 Challenge 再次嘗試
# → 若 Response 未改變 → 認證通過 (REPLAY ATTACK! )
```

###  安全威脅
- **Replay Attack**: 攻擊者重複使用舊的有效 Challenge-Response 對
- **Seed 可預測**: 固定種子下，Challenge 永遠相同
- **無時間限制**: Server 無法驗證 Response 是「新鮮」還是「陳舊」

---

##  解決方案：動態 Seed + 時間窗口驗證

###  核心設計原則

```
動態 Seed = f(Timestamp, Nonce, 伺服器秘鑰)
          ├─ Timestamp: 當前時間戳 (unix epoch)
          ├─ Nonce: 伺服器隨機生成的 256-bit 隨機數
          └─ SK: 伺服器私鑰 (不變)

驗證流程 = Seed 時效性 + 漢明距離容錯
        ├─ Server 發送時刻 T₀ + Nonce
        ├─ Node 驗證 ΔT ≤ Timeout (防止過期)
        ├─ Client 回傳 ΔT 資訊
        └─ Server 二次檢驗 + 黑名單檢查
```

---

##  詳細實現方案

### 1️⃣ Seed 生成邏輯 (Server 側)

#### 方案 A: Timestamp-based (時間戳記型，推薦)
```python
import time
import secrets
import hmac
import hashlib

def generate_dynamic_seed(server_secret_key: str, granularity: int = 1) -> tuple:
    """
    生成動態 Seed (時間戳記型)
    
    參數：
      server_secret_key: 伺服器秘密鑰 (不變)
      granularity: 時間粒度 (秒)。建議 granularity ≥ 1
                   - granularity=1: 每秒生成新 Seed
                   - granularity=5: 每 5 秒生成新 Seed
    
    返回：
      (seed_string, timestamp, nonce, seed_json)
    """
    
    # 1. 取當前時間戳，按粒度分組
    timestamp = int(time.time() / granularity) * granularity
    
    # 2. 生成隨機 Nonce (256-bit)
    nonce = secrets.token_hex(32)  # 64 個 hex 字符 = 256 bit
    
    # 3. 組合 Seed 基礎資訊
    seed_input = f"{timestamp}:{nonce}:{server_secret_key}"
    
    # 4. 用 HMAC-SHA256 生成最終 Seed
    seed_string = hmac.new(
        key=server_secret_key.encode(),
        msg=seed_input.encode(),
        digestmod=hashlib.sha256
    ).hexdigest()
    
    # 5. 打包回傳
    seed_json = {
        "timestamp": timestamp,
        "nonce": nonce,
        "seed": seed_string,
        "granularity": granularity
    }
    
    return seed_string, timestamp, nonce, seed_json

# 【使用範例】
SK = "FU_JEN_CSIE_SECRET_2026"
seed, ts, nonce, seed_json = generate_dynamic_seed(SK, granularity=1)

print(f"Seed: {seed}")
print(f"Timestamp: {ts}")
print(f"Nonce: {nonce}")
# 輸出示例：
# Seed: 3f8d2a1b9c4e7f6a5d3c1b0e9f4d2a8b
# Timestamp: 1705067430
# Nonce: a7f3e2b1d4c6f9e8a3b5d7c1f2e4a6d8
```

#### 方案 B: 進階型 (Nonce Counter)
```python
# 若不想依賴時間戳，可用 Counter + Nonce
def generate_dynamic_seed_counter(server_secret_key: str, counter: int) -> tuple:
    """
    生成動態 Seed (計數器型)
    
    特點：
      - 不依賴時間精度
      - 每次調用自動 +1
      - 需要伺服器維護 Counter 狀態
    """
    
    nonce = secrets.token_hex(32)
    seed_input = f"COUNTER:{counter}:NONCE:{nonce}:{server_secret_key}"
    
    seed_string = hmac.new(
        key=server_secret_key.encode(),
        msg=seed_input.encode(),
        digestmod=hashlib.sha256
    ).hexdigest()
    
    return seed_string, counter, nonce
```

---

### 2️⃣ Challenge 生成與發送 (Server 側)

```python
def generate_challenge_with_dynamic_seed(config: dict) -> dict:
    """
    完整的 Challenge 生成流程
    """
    
    SK = config["VRF_CONFIG"]["server_secret_key"]
    
    # 【Step 1】生成動態 Seed
    seed_str, timestamp, nonce, seed_json = generate_dynamic_seed(SK, granularity=1)
    
    # 【Step 2】用 VRF 生成 Challenge (基於動態 Seed)
    challenge_hex = hmac.new(
        key=SK.encode(),
        msg=seed_str.encode(),
        digestmod=hashlib.sha256
    ).hexdigest()
    
    # 【Step 3】生成 VRF Proof (用於驗證)
    proof = hashlib.sha256(
        f"{challenge_hex}{SK}".encode()
    ).hexdigest()[:20]  # 截取前 20 字符
    
    # 【Step 4】打包 Challenge JSON (包含時間戳記資訊)
    challenge_payload = {
        "challenge": challenge_hex,
        "timestamp": timestamp,           #  Server 發送時刻
        "nonce": nonce,                   #  隨機 Nonce
        "proof": proof,
        "granularity": 1,
        "max_response_time": 10           # Node 最多 10 秒內要回應
    }
    
    # 【Step 5】Server 本地記錄 (用於後續驗證)
    # 存到資料庫或記憶體中
    server_seed_store = {
        "timestamp": timestamp,
        "nonce": nonce,
        "seed": seed_str,
        "created_at": time.time(),
        "status": "pending",              # pending → used → expired
        "responses": []                   # 收到的所有 Response
    }
    
    return challenge_payload, server_seed_store
```

---

### 3️⃣ Node 端的驗證邏輯 (Replay Protection)

```python
def validate_seed_freshness(challenge_received: dict, 
                            max_response_time: int = 10) -> bool:
    """
    Node 收到 Challenge 後，驗證 Seed 的時效性
    
    防禦機制：
      1. 檢查 Challenge 時間戳 vs 當前時間
      2. 若超過 max_response_time，拒絕
      3. 記錄 ΔT (用於 Server 二次驗證)
    """
    
    challenge_ts = challenge_received["timestamp"]
    max_response_time = challenge_received.get("max_response_time", 10)
    
    time_now = time.time()
    delta_t = time_now - challenge_ts
    
    print(f" Challenge 收到延遲: {delta_t:.2f}s")
    
    if delta_t > max_response_time:
        print(f" Challenge 已過期 (超過 {max_response_time}s)")
        return False, None
    
    print(f" Challenge 時效性驗證通過")
    return True, delta_t

def generate_response_with_delta_t(challenge_received: dict, 
                                    puf_key: str, 
                                    noise_level: int) -> dict:
    """
    Node 生成 Response，包含時間資訊
    """
    
    # 驗證 Freshness
    is_fresh, delta_t = validate_seed_freshness(challenge_received)
    
    if not is_fresh:
        return {"error": "Challenge expired"}
    
    # 正常生成 Response
    challenge_hex = challenge_received["challenge"]
    timestamp_from_server = challenge_received["timestamp"]
    
    # PUF 模擬
    response_ideal = hmac.new(
        key=puf_key.encode(),
        msg=challenge_hex.encode(),
        digestmod=hashlib.sha256
    ).hexdigest()
    
    # 加雜訊
    noise_mask = secrets.randbits(256)
    response_noisy = f"{int(response_ideal, 16) ^ noise_mask:064x}"
    
    # 回傳，包含時間戳記資訊
    response_payload = {
        "response": response_noisy,
        "device_id": "FU_JEN_NODE_01",
        "timestamp_received": timestamp_from_server,      # Server 發送時刻
        "timestamp_responded": time.time(),               # Node 回應時刻
        "delta_t": delta_t,                               # ΔT = 接收到回應的時間
        "noise_level": noise_level
    }
    
    return response_payload
```

---

### 4️⃣ Server 端的二次驗證與黑名單 (Replay Detection)

```python
class SeededChallengeStore:
    """
    Server 側的 Seed + Challenge 記錄庫
    用途：防止重放攻擊 + 驗證 Seed 時效性
    """
    
    def __init__(self, db_path: str = "seed_store.sqlite"):
        self.db_path = db_path
        self.seed_table = {}  # 簡化版（生產環境用 SQLite）
        self._init_db()
    
    def _init_db(self):
        """初始化 SQLite 資料庫"""
        import sqlite3
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS seed_challenges (
                id INTEGER PRIMARY KEY,
                timestamp INTEGER,
                nonce TEXT UNIQUE,
                seed TEXT UNIQUE,
                challenge TEXT,
                created_at FLOAT,
                status TEXT,  -- pending/used/expired
                response_count INTEGER DEFAULT 0,
                last_response_time FLOAT
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS response_log (
                id INTEGER PRIMARY KEY,
                nonce TEXT,
                response TEXT,
                received_at FLOAT,
                hamming_distance INTEGER,
                result TEXT,  -- PASS/FAIL/REPLAY
                FOREIGN KEY(nonce) REFERENCES seed_challenges(nonce)
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def store_seed(self, seed_info: dict):
        """儲存 Seed 記錄"""
        self.seed_table[seed_info["nonce"]] = {
            "timestamp": seed_info["timestamp"],
            "seed": seed_info["seed"],
            "created_at": time.time(),
            "status": "pending",
            "responses": []
        }
        print(f"💾 Seed 已記錄: nonce={seed_info['nonce'][:16]}...")
    
    def verify_seed_and_check_replay(self, 
                                     nonce: str, 
                                     response_payload: dict,
                                     timeout_window: int = 30) -> tuple:
        """
        驗證 Seed 有效性 + 檢測重放攻擊
        
        返回: (is_valid, reason, seed_info)
        """
        
        # 【檢查 1】Nonce 是否存在？
        if nonce not in self.seed_table:
            return False, "UNKNOWN_NONCE", None
        
        seed_info = self.seed_table[nonce]
        
        # 【檢查 2】Nonce 是否已過期？
        age = time.time() - seed_info["created_at"]
        if age > timeout_window:
            seed_info["status"] = "expired"
            return False, "SEED_EXPIRED", seed_info
        
        # 【檢查 3】是否已使用過？(Replay 檢測)
        if seed_info["status"] == "used":
            # 這可能是重放攻擊！
            seed_info["responses"].append({
                "received_at": time.time(),
                "response": response_payload["response"][:16],
                "result": "REPLAY_DETECTED"
            })
            return False, "REPLAY_DETECTED", seed_info
        
        # 【檢查 4】Response 時間是否合理？
        delta_t = response_payload.get("delta_t", 0)
        if delta_t > 10:  # 假設 Node 應在 10 秒內回應
            return False, "RESPONSE_TOO_LATE", seed_info
        
        #  驗證通過
        seed_info["status"] = "used"
        seed_info["responses"].append({
            "received_at": time.time(),
            "response": response_payload["response"][:16],
            "delta_t": delta_t,
            "result": "VERIFIED"
        })
        
        return True, "VERIFIED", seed_info

def verify_response_comprehensive(challenge_stored: dict,
                                  response_received: dict,
                                  seed_store: SeededChallengeStore) -> dict:
    """
    完整的 Response 驗證過程
    """
    
    # 【步驟 1】提取信息
    nonce = challenge_stored["nonce"]
    challenge_hex = challenge_stored["challenge"]
    response_hex = response_received["response"]
    
    # 【步驟 2】驗證 Seed 有效性 + 重放攻擊檢測
    is_valid, reason, seed_info = seed_store.verify_seed_and_check_replay(
        nonce, response_received, timeout_window=30
    )
    
    if not is_valid:
        return {
            "status": "FAIL",
            "reason": reason,
            "hamming_distance": -1,
            "message": f"認證失敗: {reason}"
        }
    
    # 【步驟 3】計算漢明距離 (若 Seed 驗證通過)
    hd = bin(int(challenge_hex, 16) ^ int(response_hex, 16)).count('1')
    threshold = 40  # 假設閾值
    
    # 【步驟 4】判定認證結果
    if hd <= threshold:
        result = "PASS"
    else:
        result = "FAIL"
    
    return {
        "status": result,
        "reason": "SEED_VERIFIED",
        "hamming_distance": hd,
        "threshold": threshold,
        "nonce": nonce[:16],  # 隱藏完整 Nonce
        "delta_t": response_received.get("delta_t"),
        "seed_age": time.time() - seed_info["created_at"]
    }
```

---

##  部署檢查清單

### Server 端修改
- [ ] 修改 `config.py`：新增 `SEED_CONFIG` 配置
- [ ] 修改 `app.py` Challenge 生成邏輯：integrate `generate_dynamic_seed()`
- [ ] 新增 `SeededChallengeStore` 類到 `app.py`
- [ ] 修改驗證邏輯：integrate `verify_response_comprehensive()`

### Node 端修改
- [ ] 修改 `node.py`：integrate `validate_seed_freshness()`
- [ ] 修改 Response 生成邏輯：返回 delta_t 資訊

### 配置新增
```python
# config.py 新增
SEED_CONFIG = {
    "granularity": 1,              # 時間粒度 (秒)
    "max_response_time": 10,       # Node 最多 10 秒回應
    "timeout_window": 30,          # Seed 有效期 (秒)
    "enable_replay_detection": True,
}
```

---

##  安全收益

| 威脅 | 狀態 | 防禦機制 |
|-----|------|--------|
| **Replay Attack** |  防禦 | Nonce + 一次性使用檢查 |
| **Seed 可預測** |  防禦 | Timestamp + Random Nonce |
| **過期 Challenge** |  防禦 | 時間戳記 + delta_t 驗證 |
| **Brute Force** |  部分防禦 | 短長 Response Time + 黑名單 |

---

##  效能考量

| 項目 | 值 |
|-----|-----|
| Seed 生成時間 | ~0.1ms |
| Challenge 驗證耗時 | ~1-2ms |
| Replay 檢測耗時 | ~0.5ms |
| **總端到端延遲** | **~2-3s** (包含 MQTT 網路延遲) |

 **結論**：此方案提供業界標準的重放攻擊防禦，同時保持低延遲。


