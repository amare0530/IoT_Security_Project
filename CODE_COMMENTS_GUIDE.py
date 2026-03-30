"""
程式註解加強版本 - 核心函式詳細說明
此檔案示範 app.py 與 node.py 中較複雜函式的詳細註解方式

重點關注：
  ✅ Hamming Distance 計算的逐行說明
  ✅ VRF Challenge 生成的密碼學細節
  ✅ 位元翻轉的二進位邏輯
  ✅ MQTT 異常處理的層級結構
"""

import hashlib
import hmac
import random

# ═══════════════════════════════════════════════════════════════
# 【極度詳細註解版本】函式解析
# ═══════════════════════════════════════════════════════════════

# ─────────────────────────────────────────────────────────────
# 【app.py】漢明距離計算函數 - 詳盡版本
# ─────────────────────────────────────────────────────────────

def calculate_hamming_distance_ANNOTATED(s1, s2):
    """
    計算兩個 256 位十六進位字串的漢明距離
    
    【漢明距離的定義】
    兩個等長字串在對應位置上不相同的 bit 數
    例如：
      string1: 1010
      string2: 1100
      差異位置: 第 2 位和第 4 位
      Hamming Distance = 2
    
    【在認證中的應用】
    - Challenge: 伺服器生成的 256 位挑戰碼（理想值）
    - Response: 設備回傳的 256 位響應碼（包含製程雜訊）
    - HD ≤ Threshold → 認證通過（設備特性相符）
    - HD > Threshold → 認證失敗（設備特性不符或非法設備）
    
    【參數說明】
    s1, s2: 兩個十六進位字串
      例子: "a1b2c3d4e5f6789..." (64 個十六進位字符)
      這 64 個字符代表 256 bits (64 × 4 bits = 256 bits)
    
    【返回值】
    漢明距離 (0-256): 不相同 bit 的個數
    
    【時間複雜度】
    O(n), 其中 n = 256 (固定常數，非線性)
    
    【空間複雜度】
    O(1) (除了 bit 字串的必要空間)
    """
    
    try:
        # ═══ STEP 1: 輸入驗證 ═══
        # 檢查是否收到有效的十六進位字串
        if not s1 or not s2:
            # 空值檢查：保護程式不會因 None 而崩潰
            raise ValueError("Challenge 或 Response 不能為空")
        
        # ═══ STEP 2: 十六進位轉二進制 ═══
        # 將十六進位字串轉換為二進制表示，便於逐位比較
        
        # s1 轉換流程：
        #   輸入: "a1b2c3d4" (十六進位)
        #   Step A: int(s1, 16) → 2718936020 (十進制)
        #   Step B: bin(...) → "0b1010000110110010110000110100"
        #   Step C: [2:] → "1010000110110010110000110100" (移除前綴 "0b")
        #   Step D: .zfill(256) → 補足至 256 bits
        #
        # 為什麼要補足？
        #   因為 bin() 會忽略前導零
        #   例如十進制 1 的 bin() 是 "0b1" 而非 "0b0001"
        #   zfill(256) 確保結果永遠是 256 bits
        
        hex1 = bin(int(s1, 16))[2:].zfill(256)
        hex2 = bin(int(s2, 16))[2:].zfill(256)
        
        # 驗證轉換結果
        if len(hex1) != 256 or len(hex2) != 256:
            raise ValueError(f"位數不符: {len(hex1)}, {len(hex2)}")
        
        # ═══ STEP 3: 逐位比較與差異計數 ═══
        #
        # 使用 zip() 函數將兩個字串的同位置字符配對：
        #   hex1: "1010101010..."
        #   hex2: "1010101100..."
        #   zip() 結果: ("1","1"), ("0","0"), ("1","1"), ("0","1"), ...
        #
        # 對每一對進行比較：
        #   c1 != c2 → True 或 False
        #   sum(...) → 計算 True 的總數（Python 中 True=1, False=0）
        #
        # 例子：
        #   ("1", "1") → "1" != "1" → False → 0
        #   ("0", "1") → "0" != "1" → True → 1
        #   Total: 0+1 = 1
        
        distance = sum(c1 != c2 for c1, c2 in zip(hex1, hex2))
        
        # ═══ STEP 4: 返回結果 ═══
        # 返回的 distance 值代表：
        #   0: 完全相同（最理想情況，極罕見）
        #   1-5: 輕微差異（合法設備，有小雜訊）
        #   6-20: 中等差異（設備老化或環境不友善）
        #   > 20: 大量差異（非法設備或系統故障）
        
        return distance
        
    except ValueError as e:
        # 捕獲驗證階段的錯誤（格式錯誤、空值等）
        print(f"❌ Hex 格式錯誤: {str(e)}")
        return None
    
    except Exception as e:
        # 捕獲未預期的其他錯誤（例如記憶體不足）
        print(f"❌ 計算漢明距離時發生錯誤: {str(e)}")
        return None


# ─────────────────────────────────────────────────────────────
# 【app.py】VRF Challenge 生成 - 詳盡版本
# ─────────────────────────────────────────────────────────────

def generate_vrf_challenge_ANNOTATED(private_key, seed):
    """
    使用可驗證隨機函數 (VRF) 生成不可預測的認證挑戰碼
    
    【VRF 的三個密碼學特性】
    
    1. 確定性 (Deterministic)
       同樣的私鑰和種子 → 必定產生完全相同的 Challenge
       可用於重複驗證
    
    2. 不可預測性 (Unpredictability)  
       無私鑰的攻擊者 → 無法預測下一個 Challenge
       HMAC-SHA256 的安全性保證
    
    3. 可驗證性 (Verifiable)
       持有 Proof → 任何人能驗證 Challenge 來源的合法性
    
    【參數說明】
    private_key: 伺服器私鑰字符串
      範例: "FU_JEN_CSIE_SECRET_2026"
      長度: 通常 20-50 字符
      安全性: 應該足夠長且隨機
    
    seed: CRP 資料庫種子
      範例: "CRP_INDEX_001"
      用途: 確保不同的種子產生不同的 Challenge
      來源: 預定義的 PUF 特徵庫
    
    【返回值】
    (challenge, proof) 元組
      challenge: 256 位十六進位字符 (64 字符) 例: "a1b2c3...")
      proof: 20 字位十六進位字符 (20 字符) 例: "5a3b4c2...")
    
    【密碼學細節】
    Challenge 產生:
      C = HMAC-SHA256(私鑰, 種子)
      輸出: 256 位 (32 bytes) → 十六進位 = 64 字符
      
    Proof 產生:
      Proof = SHA256(Challenge || 私鑰)[0:20]
      流程：
        1. 串接 Challenge 和私鑰
        2. 使用 SHA256 雜湊
        3. 截取前 20 字符 (80 bits)
      用途: 驗證 Challenge 的真偽（防 MITM 攻擊）
    """
    
    try:
        # ═══ STEP 1: 輸入驗證 ═══
        # 確保私鑰和種子都不為空
        if not private_key or not seed:
            raise ValueError("私鑰和種子不能為空")
        
        # ═══ STEP 2: 使用 HMAC-SHA256 生成 Challenge ═══
        #
        # HMAC 算法流程：
        #   輸入：
        #     Key = 私鑰.encode()  (轉為 bytes)
        #     Msg = 種子.encode()  (轉為 bytes)
        #   輸出：
        #     256 位 (32 bytes) 的雜湊值
        #
        # 為什麼是 HMAC 而非普通 SHA256？
        #   HMAC = 帶鑰匙的雜湊
        #   確保只有持有私鑰的人能計算出正確的值
        #   同時保持不可逆性和不可預測性
        #
        # 為什麼是 SHA256？
        #   - 廣泛認可的密碼學雜湊函數
        #   - 輸出 256 bits，安全強度充足
        #   - 速度快（< 1μsec）
        #   - 已集成在標準庫中
        #
        # hexdigest() 輸出：
        #   十六進位字符串 (64 字符，每 4 bits 用 1 字符表示)
        #   範例："a1b2c3d4e5f6789....." (64 字符)
        
        c = hmac.new(
            private_key.encode(),    # 鑰匙：伺服器私鑰
            seed.encode(),           # 訊息：CRP 種子
            hashlib.sha256           # 雜湊算法：SHA256
        ).hexdigest()
        
        # ═══ STEP 3: 生成驗證 Proof ═══
        #
        # Proof 用來驗證以下內容：
        #   1. Challenge 確實由本伺服器產生
        #   2. Challenge 在傳輸過程中未被竄改
        #   3. 防止中間人 (MITM) 攻擊
        #
        # 生成流程：
        #   (1) 串接 Challenge 和私鑰
        #       c = "a1b2c3..." (Challenge)
        #       private_key = "FU_JEN_STATE_..."
        #       c + private_key = "a1b2c3...FU_JEN_STATE_..."
        #
        #   (2) 雜湊該串接結果
        #       SHA256("a1b2c3...FU_JEN_STATE_...") = 32 bytes
        #
        #   (3) 轉為十六進位並截取前 20 字符
        #       完整輸出：64 字符
        #       截取：前 20 字符 (80 bits)
        #
        # 為什麼只截取 20 字符？
        #   - 80 bits 的安全強度對認證足夠
        #   - 減少存儲和傳輸開銷
        #   - 平衡安全性和效率
        #
        # 驗證邏輯 (伺服器端)：
        #   收到: (Challenge_recv, Proof_recv)
        #   計算: Proof_expected = SHA256(Challenge_recv || 私鑰)[0:20]
        #   比較: if Proof_expected == Proof_recv:
        #            ✅ Challenge 合法
        #         else:
        #            ❌ Challenge 被竄改
        
        proof = hashlib.sha256(
            (c + private_key).encode()  # 串接 Challenge 和私鑰
        ).hexdigest()[:20]               # 取前 20 字符
        
        # ═══ STEP 4: 返回 Challenge 和 Proof ═══
        # 返回元組方便同時取得兩個值
        # 範例用法：
        #   c, p = generate_vrf_challenge("KEY_123", "SEED_001")
        
        return c, proof
        
    except Exception as e:
        # 捕獲生成過程中任何錯誤
        print(f"❌ VRF 生成失敗: {str(e)}")
        return None, None


# ─────────────────────────────────────────────────────────────
# 【node.py】位元翻轉模擬 PUF 雜訊 - 詳盡版本
# ─────────────────────────────────────────────────────────────

def simulate_puf_response_ANNOTATED(challenge_hex, noise_level=3):
    """
    模擬物理上不可複製函數 (PUF) 對挑戰碼的響應
    同時注入硬體製程雜訊
    
    【PUF 工作原理】
    
    真實硬體場景：
      1. PUF 利用晶片製造的隨機變異特性
      2. 對輸入 Challenge 進行「特徵提取」
      3. 由於製程變異，每個晶片產生不同特徵
      4. 同一晶片、不同時間讀取，會因為環境變化產生微小差異
      
    本軟體模擬的方法：
      1. 接收 Challenge（理想的、無雜訊的特徵值）
      2. 隨機翻轉指定數量的 bit（模擬時變雜訊）
      3. 返回帶雜訊的 Response
    
    【為什麼用隨機位元翻轉？】
    
    對應真實現象：
      Challenge    ← 理想特徵（工廠測試時）
      環境因素    ← 溫度、濕度、供電波動等
      Response    ← 實際讀取的特徵（包含雜訊）
      
    數學模型：
      Response = Challenge ⊕ (Noise Bits)
      ⊕ = XOR 操作（位元級別的異或）
    
    【參數詳解】
    
    challenge_hex: 256 位的十六進位字符最
      格式: "a1b2c3d4e5f6..." (64 個十六進位字符)
      來源: 伺服器發送的 VRF Challenge
      特性: 理想的、無雜訊的特徵值
    
    noise_level: 要翻轉的位元數 (0-256)
      0 bits  → 完全無雜訊（最理想，極少見）
      3 bits  → 輕微雜訊（推薦操作點）
      10 bits → 中度雜訊（環境較差）
      20 bits → 嚴重雜訊（系統老化或故障）
    
    【返回值】
    帶雜訊的 Response，也是 256 位十六進位字符 (64 字符)
    
    【數據流範例】
    
    輸入：
      challenge_hex = "a1b2c3d4..."
      noise_level = 3
    
    轉換過程：
      Step 1: Hex → Binary
        "a1b2" → "1010", "0001", "1011", "0010"
        完整: 256 個 0 和 1 的序列
      
      Step 2: 隨機選位置
        隨機從 0-255 中選 3 個位置
        例如：位置 [15, 127, 200]
      
      Step 3: 翻轉選定位置
        位置 15: 0 → 1
        位置 127: 1 → 0
        位置 200: 1 → 0
      
      Step 4: Binary → Hex
        翻轉後的 256 bits 轉回十六進位
        產生新的 64 字符字符串
    
    輸出：
      response = "a1b2c3d5..." (與 input 不同)
    
    【應用在認證中】
    
    Hamming Distance = popcount(Challenge ⊕ Response)
    
    若 response 由「随机位元翻轉」產生：
      HD 應約等於 noise_level (加上隨機誤差)
      
      noise_level=3  → HD ≈ 3
      noise_level=10 → HD ≈ 10
    
    認證判定：
      if HD ≤ Threshold:
          ✅ 認證通過（設備特徵相符）
      else:
          ❌ 認證失敗（特徵差異過大）
    """
    
    try:
        # ═══ STEP 1: 參數驗證 ═══
        # 確保 Challenge 不為空
        if not challenge_hex:
            raise ValueError("Challenge 不能為空")
        
        # 檢查雜訊等級的有效範圍
        # 為什麼要檢查？
        #   如果 noise_level > 256：無法翻轉超過 256 bits
        #   如果 noise_level < 0：邏輯上無意義
        if not isinstance(noise_level, int) or noise_level < 0 or noise_level > 256:
            raise ValueError(f"Noise Level 必須在 0-256 之間，收到: {noise_level}")
        
        # ═══ STEP 2: 十六進位轉二進制 ═══
        #
        # 流程：
        #   "a1b2c3d4" (十六進位)
        #     ↓
        #   int("a1b2c3d4", 16) = 2718936020 (十進制)
        #     ↓
        #   bin(2718936020) = "0b1010000110110010110000110100" (二進制字符串)
        #     ↓
        #   [2:] 移除 "0b" 前綴 = "1010000110110010110000110100"
        #     ↓
        #   .zfill(256) 補足至 256 bits = "0000...1010000110110010110000110100"
        #     ↓
        #   list(...) 轉為列表便於修改 = ['0','0','0',...,'1','0','1',...]
        #
        # 為什麼要轉列表？
        #   原始字符串不可修改 (Immutable)
        #   列表可修改 (Mutable)，允許翻轉特定位置
        
        try:
            bits = list(bin(int(challenge_hex, 16))[2:].zfill(256))
        except ValueError:
            raise ValueError(f"無效的十六進位字串: {challenge_hex[:20]}...")
        
        # ═══ STEP 3: 零雜訊的特殊情況 ═══
        # 若 noise_level=0，直接返回原 Challenge
        # 這是最理想的情況（完全無雜訊）
        if noise_level == 0:
            return challenge_hex
        
        # ═══ STEP 4: 隨機選擇翻轉位置 ═══
        #
        # random.sample() 的作用：
        #   從 range(256) 中隨機選取 noise_level 個不重複的位置
        #
        # 為什麼要"不重複"？
        #   若同一位置翻轉兩次，最終會回到原狀態
        #   我們要的是終態有 noise_level 個不同的 bits
        #
        # 例子：noise_level=3
        #   可能產生：[15, 127, 200]
        #   意義：在位置 15, 127, 200 翻轉 bits
        #
        # time 複雜度: O(noise_level)
        
        indices = random.sample(range(256), noise_level)
        
        # ═══ STEP 5: 執行位元翻轉 ═══
        #
        # 對每個選定位置進行 XOR 操作（翻轉）
        # 翻轉邏輯：
        #   if bits[i] == '0':
        #       bits[i] = '1'
        #   else if bits[i] == '1':
        #       bits[i] = '0'
        #
        # 使用三元運算子簡化：
        #   bits[i] = '1' if bits[i] == '0' else '0'
        #
        # 效果：
        #   Original: "001010..." 
        #   Flip i=0: "101010..."
        #   Flip i=2: "100010..."
        #   Flip i=5: "100000..."
        
        for i in indices:
            bits[i] = '1' if bits[i] == '0' else '0'
        
        # ═══ STEP 6: 二進制轉十六進位 ═══
        #
        # 流程（反向）：
        #   ['0','1','0',...] (列表)
        #     ↓
        #   "010..." (字符串)
        #     ↓
        #   int("010...", 2) = 十進制數字
        #     ↓
        #   hex(...) = "0x5c04..." (十六進位字符串帶 0x 前綴)
        #     ↓
        #   [2:] 移除 "0x" 前綴
        #     ↓
        #   .zfill(64) 補足至 64 字符 (256 bits / 4)
        #
        # zfill(64) 的重要性：
        #   若翻轉導致數字變小，轉十六進位時可能少於 64 字符
        #   例如十進制 255 的十六進位是 "ff" (2 字符)
        #   補足後變 "0000...00ff" (64 字符)
        
        response_hex = hex(int("".join(bits), 2))[2:].zfill(64)
        
        # ═══ STEP 7: 返回帶雜訊的 Response ═══
        # 這個 Response 會透過 MQTT 回傳給伺服器
        # 伺服器會計算 Hamming Distance 進行認證
        
        return response_hex
        
    except ValueError as e:
        # 捕獲驗證階段的錯誤
        print(f"❌ [PUF] 驗證錯誤: {str(e)}")
        return None
    
    except Exception as e:
        # 捕獲未預期的錯誤（例如記憶體不足）
        print(f"❌ [PUF] 未預期的錯誤: {str(e)}")
        return None


# ─────────────────────────────────────────────────────────────
# 【app.py】MQTT 異常處理層級 - 詳盡版本
# ─────────────────────────────────────────────────────────────

def mqtt_error_handling_hierarchy():
    """
    MQTT 異常處理的層級結構
    
    【層級 1: 連接層】
    ├─ ConnectionRefusedError
    │  原因: Broker 未運行或端口關閉
    │  應對: 提示使用者，建議檢查 Broker 狀態
    │  
    ├─ ConnectionError
    │  原因: 網路問題，無法到達 Broker
    │  應對: 重試連接，指數退避
    │
    └─ TimeoutError
       原因: 連接超時
       應對: 增加超時限制或檢查網路
    
    【層級 2: 訊息解析層】
    ├─ json.JSONDecodeError
    │  原因: 收到的訊息不是有效 JSON
    │  應對: 記錄錯誤訊息，繼續監聽
    │
    ├─ KeyError
    │  原因: JSON 中缺少預期的欄位
    │  應對: 驗證訊息結構
    │
    └─ ValueError
       原因: 值不在預期範圍
       應對: 拒絕訊息，提示使用者
    
    【層級 3: 業務邏輯層】
    ├─ 驗證失敗
    │  原因: Hamming Distance 超過閾值
    │  應對: 拒絕設備，記錄日誌
    │
    └─ 資料庫錯誤
       原因: SQLite 寫入失敗
       應對: 記錄警告，繼續運行
    
    【層級 4: 全域異常】
    └─ Exception
       備選方案，捕獲所有未預料的錯誤
       應對: 安全地終止並清理資源
    
    【最佳實踐範例】
    
    try:
        # 層級 1: 連接
        client.connect(host, port)
    except ConnectionRefusedError:
        # 特定處理連接拒絕
        show_error("Broker 未運行")
    except Exception as e_level1:
        # 通用連接層處理
        show_error(f"連接失敗: {e_level1}")
    
    try:
        # 層級 2: 訊息解析
        payload = json.loads(msg.payload.decode())
    except json.JSONDecodeError as e_level2:
        # 特定處理 JSON 錯誤
        log_error(f"JSON 格式錯誤")
        return  # 跳過此訊息，繼續監聽
    except Exception as e_level2:
        # 通用解析層處理
        log_error(str(e_level2))
    
    try:
        # 層級 3: 業務邏輯
        hd = calculate_hamming_distance(challenge, response)
        if hd is None:
            raise ValueError("計算距離失敗")
    except ValueError as e_level3:
        # 特定處理驗證錯誤
        reject_device(str(e_level3))
    except Exception as e_level3:
        # 通用業務邏輯處理
        log_error(str(e_level3))
    
    finally:
        # 層級 4: 清理資源
        # 無論是否發生異常，都要執行
        client.disconnect()
        close_database()
    """
    pass


# ═══════════════════════════════════════════════════════════════
# 【測試與驗證用例】
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 70)
    print("代碼註釋加強版本 - 函數演示")
    print("=" * 70)
    
    # 測試 1: Hamming Distance
    print("\n【測試 1】漢明距離計算")
    c1 = "a1b2c3d4e5f6789012345678901234567890123456789012345678901234567890"
    c2 = "a1b2c3d4e5f6789012345678901234567890123456789012345678901234567891"
    # 只有最後 1 個字符不同
    distance = calculate_hamming_distance_ANNOTATED(c1, c2)
    print(f"Challenge 1: {c1[:20]}...")
    print(f"Challenge 2: {c2[:20]}...")
    print(f"Hamming Distance: {distance} bits")
    
    # 測試 2: VRF Challenge 生成
    print("\n【測試 2】VRF Challenge 生成")
    sk = "FU_JEN_CSIE_SECRET_2026"
    seed = "CRP_INDEX_001"
    challenge, proof = generate_vrf_challenge_ANNOTATED(sk, seed)
    print(f"私鑰: {sk}")
    print(f"種子: {seed}")
    print(f"Challenge: {challenge[:20]}... (共 {len(challenge)} 字符)")
    print(f"Proof: {proof}")
    
    # 測試 3: PUF 模擬
    print("\n【測試 3】PUF 雜訊模擬")
    response = simulate_puf_response_ANNOTATED(challenge, noise_level=3)
    print(f"原始 Challenge: {challenge[:20]}...")
    print(f"帶雜訊 Response: {response[:20]}...")
    hd = calculate_hamming_distance_ANNOTATED(challenge, response)
    print(f"漢明距離: {hd} bits (預期約 3 bits)")

print("\n" + "=" * 70)
print("說明: 本文件為代碼註釋示意版")
print("完整版請參考 app.py 和 node.py")
print("=" * 70)
