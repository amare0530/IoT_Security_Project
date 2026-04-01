"""
═══════════════════════════════════════════════════════════════════
PUF 模擬器 - 高斯雜訊模型版本
Phase 2: 科學化的實驗數據生成
═══════════════════════════════════════════════════════════════════

改進點：
  ✅ 高斯雜訊模型 (Gaussian Noise Model)
  ✅ 機率驅動的位元翻轉 (Probabilistic Bit Flip)
  ✅ 可調整的雜訊強度參數 (σ = 0.01 ~ 0.20)
  ✅ 真實硬體統計模擬
  ✅ 時間變異性支持

原理：
  在真實硬體 (SRAM PUF, RO-PUF) 中，PUF 回應不是完全確定的。
  每次讀取都會受到環境噪音的影響（溫度、電壓、製程變異）。
  
  因此，我們用二項分佈模型：
    Pr(bit_flip) = σ (高斯噪音標準差)
  
  例如 σ=0.05 表示 5% 的位元會隨機翻轉。

作者: IoT Security Project - Phase 2
日期: 2026.03.31
"""

import hashlib
import hmac
import json
import random
import time
from typing import Tuple, Dict, Optional, Set
import math

# ═══════════════════════════════════════════════════════════════
# 【配置】
# ═══════════════════════════════════════════════════════════════

class PUFConfig:
    """PUF 模擬器配置"""
    
    def __init__(
      self,
      response_bits: int = 256,
      noise_sigma: float = 0.03,
      use_hamming74_ecc: bool = False,
      use_ecc_interleaving: bool = False,
      ecc_interleaving_depth: int = 8,
      cluster_noise_prob: float = 0.02,
      cluster_size: int = 4,
      bias_ratio: float = 0.10,
      unstable_ratio: float = 0.08,
      bias_strength: float = 0.90,
      unstable_extra_noise: float = 0.08,
      env_noise_sigma: float = 0.005,
      env_spike_prob: float = 0.05,
      env_spike_min: float = 0.05,
      env_spike_max: float = 0.12,
    ):
        """
        参数：
          response_bits: PUF 回應位寬 (通常 256 bit)
          noise_sigma: 雜訊標準差 (σ), 範圍 0.01 ~ 0.20
                      - 0.01 = 1% 位元翻轉 (低雜訊)
                      - 0.05 = 5% 位元翻轉 (中等雜訊) ⭐ 推薦
                      - 0.10 = 10% 位元翻轉 (高雜訊)
                      - 0.20 = 20% 位元翻轉 (極端雜訊)
          
          bias_ratio: 受製造缺陷影響的位元比例 (推薦 0.10 = 10%)
          bias_strength: 偏壓強度 (推薦 0.90 = 強力固定)
        """
        self.response_bits = response_bits
        self.noise_sigma = noise_sigma
        self.use_hamming74_ecc = use_hamming74_ecc
        self.use_ecc_interleaving = use_ecc_interleaving
        self.ecc_interleaving_depth = ecc_interleaving_depth
        self.cluster_noise_prob = cluster_noise_prob
        self.cluster_size = cluster_size
        self.bias_ratio = bias_ratio
        self.unstable_ratio = unstable_ratio
        self.bias_strength = bias_strength
        self.unstable_extra_noise = unstable_extra_noise
        self.env_noise_sigma = env_noise_sigma
        self.env_spike_prob = env_spike_prob
        self.env_spike_min = env_spike_min
        self.env_spike_max = env_spike_max
    
    def validate(self):
        """驗證配置合理性"""
        assert 0.001 <= self.noise_sigma <= 0.50, f"Noise sigma 必须在 0.001~0.50 之間"
        assert self.response_bits > 0, f"Response bits 必须 > 0"
        if self.use_hamming74_ecc:
          assert self.response_bits % 4 == 0, "使用 Hamming(7,4) 時 response_bits 必须為 4 的倍數"
          assert self.ecc_interleaving_depth >= 2, "ecc_interleaving_depth 必须 >= 2"
        assert 0.0 <= self.cluster_noise_prob <= 1.0, "cluster_noise_prob 必须在 0.0~1.0 之間"
        assert self.cluster_size >= 2, "cluster_size 必须 >= 2"
        assert 0.0 <= self.bias_ratio <= 0.50, f"bias_ratio 必须在 0.0~0.50 之間"
        assert 0.0 <= self.unstable_ratio <= 0.50, f"unstable_ratio 必须在 0.0~0.50 之間"
        assert 0.0 <= self.bias_strength <= 1.0, f"bias_strength 必须在 0.0~1.0 之間"
        assert 0.0 <= self.unstable_extra_noise <= 0.50, f"unstable_extra_noise 必须在 0.0~0.50 之間"
        assert 0.0 <= self.env_noise_sigma <= 0.20, f"env_noise_sigma 必须在 0.0~0.20 之間"
        assert 0.0 <= self.env_spike_prob <= 1.0, f"env_spike_prob 必须在 0.0~1.0 之間"
        assert 0.0 <= self.env_spike_min <= 0.50, f"env_spike_min 必须在 0.0~0.50 之間"
        assert self.env_spike_min <= self.env_spike_max <= 0.50, f"env_spike_max 必须在 env_spike_min~0.50 之間"


# ═══════════════════════════════════════════════════════════════
# 【PUF 核心邏輯】
# ═══════════════════════════════════════════════════════════════

class PUFSimulator:
    """
    高斯雜訊模型的 PUF 模擬器
    
    工作流程：
      1. Challenge 輸入 → 確定性響應 (Ideal Response)
      2. 注入高斯雜訊 → 位元翻轉
      3. 時間變異性 → 每次讀取略有不同
    """
    
    def __init__(self, puf_key: str, config: PUFConfig = None):
        """
        初始化 PUF 模擬器
        
        參數：
          puf_key: PUF 的物理特性密鑰 (唯一 per 設備)
          config: PUFConfig 對象
        """
        self.puf_key = puf_key
        self.config = config or PUFConfig()
        self.config.validate()
        self.noise_channel_bits = self._effective_noise_bits()

        # 每顆裝置都有固定的位元偏壓與不穩定位元分佈。
        self._rng = random.Random(f"{self.puf_key}_layout_seed")
        self.bias_map = self._build_bias_map()
        self.unstable_bits = self._build_unstable_bits()

    def _effective_noise_bits(self) -> int:
        if self.config.use_hamming74_ecc:
            # 4 data bits -> 7 code bits
            return (self.config.response_bits // 4) * 7
        return self.config.response_bits

    def _build_bias_map(self) -> Dict[int, float]:
        """
        建立位元偏壓地圖。

        返回：
          {bit_index: pr(bit=1)}
        """
        num_bias_bits = int(self.noise_channel_bits * self.config.bias_ratio)
        chosen_bits = self._rng.sample(range(self.noise_channel_bits), num_bias_bits)

        bias_map: Dict[int, float] = {}
        for bit_idx in chosen_bits:
            # 偏壓位元通常接近 0 或 1，而不是 0.5。
            if self._rng.random() < 0.5:
                bias_map[bit_idx] = self._rng.uniform(0.05, 0.25)
            else:
                bias_map[bit_idx] = self._rng.uniform(0.75, 0.95)
        return bias_map

    def _build_unstable_bits(self) -> Set[int]:
        """建立高噪聲的不穩定位元集合。"""
        num_unstable_bits = int(self.noise_channel_bits * self.config.unstable_ratio)
        return set(self._rng.sample(range(self.noise_channel_bits), num_unstable_bits))

    @staticmethod
    def _hamming74_encode_nibble(nibble: str) -> str:
        d1, d2, d3, d4 = [int(x) for x in nibble]
        p1 = d1 ^ d2 ^ d4
        p2 = d1 ^ d3 ^ d4
        p3 = d2 ^ d3 ^ d4
        return f"{p1}{p2}{d1}{p3}{d2}{d3}{d4}"

    @staticmethod
    def _hamming74_decode_codeword(code7: str) -> str:
        bits = [int(x) for x in code7]
        s1 = bits[0] ^ bits[2] ^ bits[4] ^ bits[6]
        s2 = bits[1] ^ bits[2] ^ bits[5] ^ bits[6]
        s3 = bits[3] ^ bits[4] ^ bits[5] ^ bits[6]
        syndrome = s1 + (s2 << 1) + (s3 << 2)

        if 1 <= syndrome <= 7:
            bits[syndrome - 1] ^= 1

        return f"{bits[2]}{bits[4]}{bits[5]}{bits[6]}"

    def _hamming74_encode_bits(self, bitstr: str) -> str:
      encoded = []
      for i in range(0, len(bitstr), 4):
        encoded.append(self._hamming74_encode_nibble(bitstr[i:i+4]))

      channel_bits = "".join(encoded)
      if self.config.use_ecc_interleaving:
        return self._interleave_bits(channel_bits, self.config.ecc_interleaving_depth)
      return channel_bits

    def _hamming74_decode_bits(self, encoded_bitstr: str) -> str:
      channel_bits = encoded_bitstr
      if self.config.use_ecc_interleaving:
        channel_bits = self._deinterleave_bits(encoded_bitstr, self.config.ecc_interleaving_depth)

      decoded = []
      for i in range(0, len(channel_bits), 7):
        decoded.append(self._hamming74_decode_codeword(channel_bits[i:i+7]))
      return "".join(decoded)

    @staticmethod
    def _interleave_bits(bitstr: str, depth: int) -> str:
      """把連續位元打散，降低 burst error 對單一區塊 ECC 的破壞。"""
      d = max(2, depth)
      cols = math.ceil(len(bitstr) / d)
      padded_len = d * cols
      padded = bitstr.ljust(padded_len, "0")

      out = []
      for c in range(cols):
        for r in range(d):
          out.append(padded[r * cols + c])

      return "".join(out)[:len(bitstr)]

    @staticmethod
    def _deinterleave_bits(bitstr: str, depth: int) -> str:
      """_interleave_bits 的逆操作。"""
      d = max(2, depth)
      cols = math.ceil(len(bitstr) / d)
      padded_len = d * cols
      interleaved = bitstr.ljust(padded_len, "0")

      matrix = [["0"] * cols for _ in range(d)]
      idx = 0
      for c in range(cols):
        for r in range(d):
          matrix[r][c] = interleaved[idx]
          idx += 1

      out = []
      for r in range(d):
        out.extend(matrix[r])
      return "".join(out)[:len(bitstr)]

    @staticmethod
    def _clamp(prob: float, low: float = 0.0, high: float = 1.0) -> float:
        return max(low, min(high, prob))

    def _sample_environment_noise(self) -> float:
        """
        每次讀取都抽樣一次環境擾動。
        用 |N(0, sigma)| 反映溫度/電壓變化通常只會讓穩定性變差。
        """
        env_noise = abs(random.gauss(0.0, self.config.env_noise_sigma))
        # 罕見尖峰模擬：高溫/壓降瞬態會讓一次讀取顯著惡化。
        if random.random() < self.config.env_spike_prob:
            env_noise += random.uniform(self.config.env_spike_min, self.config.env_spike_max)
        return env_noise

    def _bit_flip_probability(self, bit_idx: int, ideal_bit: int, env_noise: float) -> float:
        """計算單一位元的翻轉機率。"""
        
        # 【Phase 1 Enhancement】 偏壓位強制固定化
        # 根據用戶指令，偏壓位應該表現為「製造缺陷」：基本不翻轉
        if bit_idx in self.bias_map:
            # 偏壓位基本固定，翻轉機率大幅降低
            # target_one_prob 是該位「傾向1」的機率
            target_one_prob = self.bias_map[bit_idx]
            
            # 偏壓位的翻轉機率非常低（製造缺陷永久性）
            if ideal_bit == 1:
                # 若位元應該是1，但偏壓傾向0，則翻轉到0的機率很高
                p_flip = max(0.0, 0.5 - target_one_prob) * self.config.bias_strength
            else:
                # 若位元應該是0，但偏壓傾向1，則翻轉到1的機率很高
                p_flip = max(0.0, target_one_prob - 0.5) * self.config.bias_strength
            
            return self._clamp(p_flip, 0.0, 0.20)  # 限制在 0~20%，確保固定性

        # 【未偏壓位】正常的環境雜訊處理
        # 偏壓位越強，未偏壓位的雜訊應該越低（相對重要性降低）
        adjusted_noise = self.config.noise_sigma * (1.0 - self.config.bias_strength * 0.3)
        p_flip = adjusted_noise + env_noise

        if bit_idx in self.unstable_bits:
            p_flip += self.config.unstable_extra_noise

        return self._clamp(p_flip)

    def apply_cluster_noise(self, noisy_int: int, cluster_size: int = 4) -> int:
        """
        模擬群聚雜訊：相鄰位元在同一事件中集體翻轉。

        物理意義：電壓跌落或局部熱斑會造成 SRAM 鄰近 cell 同步失效。
        """
        if self.config.cluster_noise_prob <= 0.0:
            return noisy_int

        csize = max(2, cluster_size)
        out = noisy_int

        for start in range(0, self.noise_channel_bits, csize):
            if random.random() < self.config.cluster_noise_prob:
                end = min(start + csize, self.noise_channel_bits)
                for bit_idx in range(start, end):
                    out ^= (1 << bit_idx)

        return out
    
    def generate_ideal_response(self, challenge: str) -> str:
        """
        生成理想響應 (無雜訊)
        
        原理：
          用 HMAC 來模擬 PUF 的確定性行為
          相同的 Challenge 總是返回相同的理想響應
        
        參數：
          challenge: Challenge Hex 字串
        
        返回：
          理想響應 (Hex 字串，256 bit)
        """
        ideal = hmac.new(
            key=self.puf_key.encode('utf-8'),
            msg=challenge.encode('utf-8'),
            digestmod=hashlib.sha256
        ).hexdigest()
        
        return ideal
    
    def add_gaussian_noise(self, ideal_response: str) -> str:
        """
        注入高斯雜訊，模擬真實硬體的時間變異性
        
        原理：
          對於每一位元，以機率 σ 將其翻轉。
          這模擬了環境雜訊對 PUF 讀取的影響。
          
          數學上：
            Pr(bit_flip) = σ (標準差)
            每位被翻轉的位元數 ~= Binomial(n=256, p=σ)
        
        參數：
          ideal_response: 理想響應
        
        返回：
          帶雜訊的響應
        """
        # 1. 將 Hex 轉為 bitstring（固定 response_bits 長度）
        ideal_bits = bin(int(ideal_response, 16))[2:].zfill(self.config.response_bits)

        # 2. 可選 ECC：先將 256-bit data 編碼為 448-bit code（Hamming 7,4）
        if self.config.use_hamming74_ecc:
            noise_channel_bits = self._hamming74_encode_bits(ideal_bits)
        else:
            noise_channel_bits = ideal_bits

        noise_int = int(noise_channel_bits, 2)

        # 3. 模擬當前讀取的環境擾動（溫度/電壓漂移）
        env_noise = self._sample_environment_noise()

        # 4. 逐位元決定是否翻轉，翻轉機率受偏壓與不穩定位元影響
        bits_to_flip = []
        for bit_idx in range(self.noise_channel_bits):
            ideal_bit = (noise_int >> bit_idx) & 0x1
            p_flip = self._bit_flip_probability(bit_idx, ideal_bit, env_noise)
            if random.random() < p_flip:
                bits_to_flip.append(bit_idx)

        # 5. 執行位元翻轉
        noisy_int = noise_int
        for bit_idx in bits_to_flip:
            noisy_int ^= (1 << bit_idx)

        # 5.1 額外群聚雜訊（非 IID）
        noisy_int = self.apply_cluster_noise(noisy_int, cluster_size=self.config.cluster_size)

        noisy_channel_bits = bin(noisy_int)[2:].zfill(self.noise_channel_bits)

        # 6. 可選 ECC：把 noisy code 解碼回 256-bit data
        if self.config.use_hamming74_ecc:
            corrected_bits = self._hamming74_decode_bits(noisy_channel_bits)
        else:
            corrected_bits = noisy_channel_bits

        # 7. 轉回 64-char hex（固定 256-bit）
        noisy_response = hex(int(corrected_bits, 2))[2:].zfill(self.config.response_bits // 4)

        return noisy_response
    
    def generate_response(self, challenge: str, add_noise: bool = True) -> Tuple[str, str]:
        """
        生成 PUF 響應（可選雜訊）
        
        參數：
          challenge: Challenge Hex 字串
          add_noise: 是否添加高斯雜訊（True = 真實模式，False = 理想模式）
        
        返回：
          (ideal_response, noisy_response)
        """
        # 生成理想響應
        ideal = self.generate_ideal_response(challenge)
        
        # 可選地添加雜訊
        if add_noise:
            noisy = self.add_gaussian_noise(ideal)
        else:
            noisy = ideal
        
        return ideal, noisy
    
    def get_hamming_distance(self, resp1: str, resp2: str) -> int:
        """
        計算兩個響應之間的漢明距離
        
        定義：
          HD = 兩個二進制字串中位元不同的個數
        
        參數：
          resp1, resp2: 兩個 Hex 字串
        
        返回：
          漢明距離 (0~256)
        """
        int1 = int(resp1, 16)
        int2 = int(resp2, 16)
        xor_result = int1 ^ int2
        hd = bin(xor_result).count('1')
        return hd


# ═══════════════════════════════════════════════════════════════
# 【認證與決策邏輯】
# ═══════════════════════════════════════════════════════════════

class AuthenticationEngine:
    """
    認證引擎 - 計算 FAR/FRR + 防重放攻擊

    【Phase 1】基本認證：
    FAR = False Accept Rate (誤接受率)
          = Pr(冒充者被接受)
          = 冒充者成功的次數 / 冒充者嘗試總數
    
    FRR = False Rejection Rate (誤拒絕率)
          = Pr(合法用戶被拒絕)
          = 合法用戶失敗的次數 / 合法用戶嘗試總數
    
    EER (Equal Error Rate)
          = FAR = FRR 時的點 (通常用於評估系統性能)

    【Phase 2】Anti-Replay Protection (新增):
    - Nonce 快取：紀錄已使用過的一次性隨機數
    - 防禦重放攻擊 (Replay Attack)
      駭客若側錄曾經成功的 <Challenge, Response> 組合，
      在沒有繞過 Nonce 機制的情況下，無法重複使用
    """
    
    def __init__(
        self,
        threshold: int = 40,
        helper_integrity_key: Optional[str] = None,
        use_privacy_amplification: bool = True,
        privacy_threshold: int = 0,
      enforce_privacy_gate: bool = False,
    ):
        """
        參數：
          threshold: 漢明距離閾值
                    如果 HD ≤ threshold → 接受
                    如果 HD > threshold → 拒絕
        """
        self.threshold = threshold
        # 【Phase 2】Nonce 快取 - 存儲已使用過的一次性隨機數
        self.used_nonces: Set[str] = set()
        self.nonce_cache_size_limit = 1000  # 防止記憶體無限增長
        # Enrollment 存儲：challenge -> helper record（公開 helper + integrity tag）
        self.helper_data_store: Dict[str, Dict[str, str]] = {}
        self.helper_integrity_key = helper_integrity_key or "LOCAL_DEV_HELPER_KEY_CHANGE_IN_PRODUCTION"
        self.use_privacy_amplification = use_privacy_amplification
        self.privacy_threshold = max(0, privacy_threshold)
        self.enforce_privacy_gate = enforce_privacy_gate

    @staticmethod
    def _hamming74_parity_for_nibble(nibble_bits: str) -> str:
        """對 4-bit data 計算 Hamming(7,4) 的 3 個 parity bits。"""
        d1, d2, d3, d4 = [int(x) for x in nibble_bits]
        p1 = d1 ^ d2 ^ d4
        p2 = d1 ^ d3 ^ d4
        p3 = d2 ^ d3 ^ d4
        return f"{p1}{p2}{p3}"

    @staticmethod
    def _pack_bits_to_hex(bits: str) -> str:
        """把 bit 字串打包為 hex。"""
        padded = bits + ("0" * ((4 - len(bits) % 4) % 4))
        return hex(int(padded, 2))[2:].zfill(len(padded) // 4)

    @staticmethod
    def _unpack_hex_to_bits(hex_str: str, bit_length: int) -> str:
        """把 hex 還原為固定長度 bit 字串。"""
        return bin(int(hex_str, 16))[2:].zfill(bit_length)

    @staticmethod
    def _hamming74_decode_codeword(code7: str) -> str:
        """單一 Hamming(7,4) codeword 解碼與單位元修復。"""
        bits = [int(x) for x in code7]
        s1 = bits[0] ^ bits[2] ^ bits[4] ^ bits[6]
        s2 = bits[1] ^ bits[2] ^ bits[5] ^ bits[6]
        s3 = bits[3] ^ bits[4] ^ bits[5] ^ bits[6]
        syndrome = s1 + (s2 << 1) + (s3 << 2)
        if 1 <= syndrome <= 7:
            bits[syndrome - 1] ^= 1
        return f"{bits[2]}{bits[4]}{bits[5]}{bits[6]}"

    def generate_helper_data(self, expected_response: str) -> str:
        """
        由 enrollment 參考響應生成 helper data（僅 parity）。

        安全警語：
          本實作會導致有效金鑰長度從 256-bit 降至 146-bit。
          這是教學版 helper-data 模型，並非完整 fuzzy extractor。
        """
        bits = bin(int(expected_response, 16))[2:].zfill(256)
        helper_bits = []
        for i in range(0, 256, 4):
            helper_bits.append(self._hamming74_parity_for_nibble(bits[i:i+4]))
        # 256 data bits -> 64 nibbles -> 192 helper bits
        return self._pack_bits_to_hex("".join(helper_bits))

    def _helper_integrity_tag(self, challenge: str, helper_hex: str) -> str:
        """為 helper data 計算 HMAC 標籤，防止可見但可改的資料被靜默篡改。"""
        payload = f"{challenge}|{helper_hex}".encode("utf-8")
        return hmac.new(
            key=self.helper_integrity_key.encode("utf-8"),
            msg=payload,
            digestmod=hashlib.sha256,
        ).hexdigest()

    def verify_helper_data_integrity(self, challenge: str, helper_hex: str, helper_tag: str) -> bool:
        """常數時間驗證 helper data 是否被篡改。"""
        expected_tag = self._helper_integrity_tag(challenge, helper_hex)
        return hmac.compare_digest(expected_tag, helper_tag)

    def enroll_challenge(self, challenge: str, expected_response: str) -> Dict[str, str]:
        """Enrollment 階段：為 challenge 註冊 helper data。"""
        helper_hex = self.generate_helper_data(expected_response)
        helper_tag = self._helper_integrity_tag(challenge, helper_hex)

        record = {
            "helper_hex": helper_hex,
            "helper_tag": helper_tag,
            "version": "hamming74+hmac-v1"
        }
        self.helper_data_store[challenge] = record
        return record

    def reconstruct_response_with_helper(self, raw_response: str, helper_hex: str) -> str:
        """
        驗證階段：用 helper data 對 raw noisy response 做 Hamming(7,4) 修復。
        """
        raw_bits = bin(int(raw_response, 16))[2:].zfill(256)
        helper_bits = self._unpack_hex_to_bits(helper_hex, 192)

        corrected_chunks = []
        hidx = 0
        for i in range(0, 256, 4):
            d = raw_bits[i:i+4]
            p = helper_bits[hidx:hidx+3]
            hidx += 3

            # codeword 佈局: p1 p2 d1 p3 d2 d3 d4
            code7 = f"{p[0]}{p[1]}{d[0]}{p[2]}{d[1]}{d[2]}{d[3]}"
            corrected_chunks.append(self._hamming74_decode_codeword(code7))

        corrected_bits = "".join(corrected_chunks)
        return hex(int(corrected_bits, 2))[2:].zfill(64)

    @staticmethod
    def _privacy_amplify_response(response_hex: str) -> str:
        """用 SHA-256 做熵擠壓，降低偏壓與相關性對最終金鑰的影響。"""
        normalized = response_hex.strip().lower()
        # fromhex 要求偶數長度，理論上 256-bit 是 64 chars，這裡做防呆補零。
        if len(normalized) % 2 == 1:
            normalized = "0" + normalized
        response_bytes = bytes.fromhex(normalized)
        return hashlib.sha256(response_bytes).hexdigest()
    
    def authenticate(self, hd: int) -> bool:
        """
        根據漢明距離判定認證結果
        
        返回：
          True = 認證通過，False = 認證失敗
        """
        return hd <= self.threshold
    
    def verify_session(
        self,
        response: str,
        expected_response: str,
        nonce: str,
        challenge: Optional[str] = None,
        server_timestamp: Optional[float] = None,
        max_age_seconds: int = 60,
    ) -> Dict:
        """
        【Phase 2】Session-based 認證 - 包含重放攻擊防護
        
        實現邏輯：
        1. 檢查 Nonce 是否已使用過（防重放）
        2. 如果使用過 → 回傳 "Auth Failed (Replay Detected)"
        3. 如果首次使用 → 執行漢明距離認證
        4. 認證成功 → 將 Nonce 加入快取
        
        參數：
          response: 用戶提供的 PUF 回應 (Hex string)
          expected_response: 期望的 PUF 回應 (伺服器存儲的理想值)
          nonce: 本次認證的一次性隨機數 (防重放用)
        
        返回：
          {
            "authenticated": bool,
            "reason": "Auth Success" | "Auth Failed (HD exceeded)" | "Auth Failed (Replay Detected)",
            "hd": int,
            "nonce_used": bool,
            "threshold": int
          }
        """
        # 0. 檢查時間戳是否過期（協議層時效性防護）
        if server_timestamp is not None and not self._is_timestamp_valid(server_timestamp, max_age_seconds):
            return {
                "authenticated": False,
                "reason": "Auth Failed (Timestamp Expired)",
                "hd": -1,
                "nonce_used": False,
                "threshold": self.threshold,
                "timestamp_valid": False,
                "security_note": f"server_timestamp 超過 {max_age_seconds} 秒有效窗口"
            }

        # 1. 檢查 Nonce - 防重放攻擊
        if nonce in self.used_nonces:
            return {
                "authenticated": False,
                "reason": "Auth Failed (Replay Detected)",
                "hd": -1,
                "nonce_used": True,
                "threshold": self.threshold,
                "security_note": "此 Nonce 已被使用過。攻擊者試圖重新提交舊的認證。"
            }
        
        # 2. 使用 helper data（若 challenge 已 enrollment）進行重建
        response_for_compare = response
        helper_used = False
        helper_integrity_ok = None
        if challenge is not None and challenge in self.helper_data_store:
            record = self.helper_data_store[challenge]

            # 向後相容：舊版只存 helper_hex 字串。
            if isinstance(record, str):
                helper_hex = record
                helper_tag = ""
                helper_integrity_ok = True
            else:
                helper_hex = record["helper_hex"]
                helper_tag = record.get("helper_tag", "")
                helper_integrity_ok = self.verify_helper_data_integrity(challenge, helper_hex, helper_tag)

            if helper_integrity_ok is False:
                return {
                    "authenticated": False,
                    "reason": "Auth Failed (Helper Data Tampered)",
                    "hd": -1,
                    "raw_hd": -1,
                    "pa_hd": -1,
                    "nonce_used": False,
                    "threshold": self.threshold,
                    "timestamp_valid": True,
                    "helper_data_used": True,
                    "helper_integrity_ok": False,
                    "security_note": "Helper data HMAC 驗證失敗，疑似遭到篡改。"
                }

            response_for_compare = self.reconstruct_response_with_helper(
                raw_response=response,
                helper_hex=helper_hex
            )
            helper_used = True

        # 3. 計算漢明距離（保留原始統計）
        raw_hd = self._compute_hamming_distance_from_hex(response_for_compare, expected_response)
        
        # 4. 先做原始 HD 門檻檢查
        raw_auth_ok = self.authenticate(raw_hd)

        # 5. 隱私放大：將糾錯後響應擠壓到均勻雜湊空間再比對
        pa_hd = -1
        pa_auth_ok = True
        if self.use_privacy_amplification:
            pa_response = self._privacy_amplify_response(response_for_compare)
            pa_expected = self._privacy_amplify_response(expected_response)
            pa_hd = self._compute_hamming_distance_from_hex(pa_response, pa_expected)

            if self.privacy_threshold == 0:
                # 最嚴格模式：常數時間完全匹配
                pa_auth_ok = hmac.compare_digest(pa_response, pa_expected)
            else:
                pa_auth_ok = pa_hd <= self.privacy_threshold

        auth_result = raw_auth_ok and (pa_auth_ok if self.enforce_privacy_gate else True)
        
        # 6. 如果認證成功，記錄 Nonce（防止將來重複使用）
        if auth_result:
            self.used_nonces.add(nonce)
            
            # 防止快取無限增長
            if len(self.used_nonces) > self.nonce_cache_size_limit:
                # 簡單的 FIFO 清理（實際應使用 TTL 或 LRU）
                # 移除最早的 20% 沒用過的 Nonce
                nonces_to_remove = list(self.used_nonces)[:self.nonce_cache_size_limit // 5]
                for old_nonce in nonces_to_remove:
                    self.used_nonces.discard(old_nonce)
        
        return {
            "authenticated": auth_result,
            "reason": "Auth Success" if auth_result else "Auth Failed (HD exceeded)",
            "hd": raw_hd,
            "raw_hd": raw_hd,
            "pa_hd": pa_hd,
            "nonce_used": False,
            "threshold": self.threshold,
            "timestamp_valid": True,
            "helper_data_used": helper_used,
            "helper_integrity_ok": helper_integrity_ok,
            "privacy_amplification_used": self.use_privacy_amplification,
            "privacy_threshold": self.privacy_threshold,
            "privacy_gate_enforced": self.enforce_privacy_gate,
            "cache_size": len(self.used_nonces)
        }

    @staticmethod
    def _is_timestamp_valid(server_timestamp: float, max_age_seconds: int = 60) -> bool:
        """檢查時間戳是否仍在有效窗口內。"""
        now = time.time()
        return abs(now - float(server_timestamp)) <= max_age_seconds
    
    def _compute_hamming_distance_from_hex(self, hex1: str, hex2: str) -> int:
        """計算兩個 Hex 字串的漢明距離"""
        int1 = int(hex1, 16)
        int2 = int(hex2, 16)
        xor_result = int1 ^ int2
        return bin(xor_result).count('1')
    
    def clear_nonce_cache(self):
        """清除 Nonce 快取（測試用）"""
        self.used_nonces.clear()
    
    def compute_metrics(self, genuine_hds: list, impostor_hds: list) -> Dict:
        """
        計算 FAR 和 FRR
        
        參數：
          genuine_hds: 合法用戶的漢明距離列表
          impostor_hds: 冒充者的漢明距離列表
        
        返回：
          包含 FAR, FRR, EER 等指標的字典
        """
        genuine_pass = sum(1 for hd in genuine_hds if self.authenticate(hd))
        genuine_total = len(genuine_hds)
        
        impostor_pass = sum(1 for hd in impostor_hds if self.authenticate(hd))
        impostor_total = len(impostor_hds)
        
        # FAR: 冒充者被接受的比例
        far = impostor_pass / impostor_total if impostor_total > 0 else 0.0
        
        # FRR: 合法用戶被拒絕的比例
        frr = (genuine_total - genuine_pass) / genuine_total if genuine_total > 0 else 0.0
        
        return {
            "threshold": self.threshold,
            "genuine_total": genuine_total,
            "genuine_pass": genuine_pass,
            "impostor_total": impostor_total,
            "impostor_pass": impostor_pass,
            "FAR": far,
            "FRR": frr,
            "accuracy": (genuine_pass + (impostor_total - impostor_pass)) / (genuine_total + impostor_total) if (genuine_total + impostor_total) > 0 else 0.0
        }


# ═══════════════════════════════════════════════════════════════
# 【數據記錄】
# ═══════════════════════════════════════════════════════════════

class TestRecord:
    """單次測試的完整記錄"""
    
    def __init__(self, 
                 challenge: str,
                 test_type: str,  # "genuine" or "impostor"
                 ideal_response: str,
                 noisy_response: str,
                 hamming_distance: int,
                 threshold: int,
                 result: bool):
        
        self.challenge = challenge[:16]  # 截斷顯示
        self.test_type = test_type
        self.ideal_response = ideal_response[:16]
        self.noisy_response = noisy_response[:16]
        self.hamming_distance = hamming_distance
        self.threshold = threshold
        self.result = result
        self.timestamp = time.time()
    
    def to_dict(self) -> dict:
        """轉為字典（用於 CSV 匯出）"""
        return {
            "timestamp": self.timestamp,
            "test_type": self.test_type,
            "challenge": self.challenge,
            "ideal_response": self.ideal_response,
            "noisy_response": self.noisy_response,
            "hamming_distance": self.hamming_distance,
            "threshold": self.threshold,
            "result": "PASS" if self.result else "FAIL"
        }


# ═══════════════════════════════════════════════════════════════
# 【工具函數】
# ═══════════════════════════════════════════════════════════════

def generate_challenge(
  seed: str = None,
  device_id: str = None,
  server_timestamp: Optional[float] = None,
  random_nonce: str = None,
) -> str:
  """
  生成 Challenge。

  Dynamic 模式（建議）：
    Challenge = SHA256(device_id + server_timestamp + random_nonce)

  向後相容模式：
    若未提供上述三項，則使用 seed（或當前時間）生成。
  """
  if device_id is not None and server_timestamp is not None and random_nonce is not None:
    payload = f"{device_id}|{float(server_timestamp):.6f}|{random_nonce}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()

  if seed is None:
    seed = str(time.time())
  return hashlib.sha256(seed.encode("utf-8")).hexdigest()


def print_stats(records: list, label: str = ""):
    """列印統計數據"""
    print(f"\n{'='*70}")
    print(f"📊 統計數據 {label}")
    print(f"{'='*70}")
    
    if not records:
        print("❌ 沒有記錄")
        return
    
    genuine_hds = [r.hamming_distance for r in records if r.test_type == "genuine"]
    impostor_hds = [r.hamming_distance for r in records if r.test_type == "impostor"]
    
    if genuine_hds:
        print(f"✅ 合法用戶 (Genuine):")
        print(f"   計數: {len(genuine_hds)}")
        print(f"   HD 平均值: {sum(genuine_hds)/len(genuine_hds):.2f}")
        print(f"   HD 範圍: [{min(genuine_hds)}, {max(genuine_hds)}]")
    
    if impostor_hds:
        print(f"❌ 冒充者 (Impostor):")
        print(f"   計數: {len(impostor_hds)}")
        print(f"   HD 平均值: {sum(impostor_hds)/len(impostor_hds):.2f}")
        print(f"   HD 範圍: [{min(impostor_hds)}, {max(impostor_hds)}]")
    
    print(f"{'='*70}\n")
