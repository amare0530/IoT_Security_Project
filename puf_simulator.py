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
from typing import Tuple, Dict, Optional
import math

# ═══════════════════════════════════════════════════════════════
# 【配置】
# ═══════════════════════════════════════════════════════════════

class PUFConfig:
    """PUF 模擬器配置"""
    
    def __init__(self, response_bits: int = 256, noise_sigma: float = 0.05):
        """
        参数：
          response_bits: PUF 回應位寬 (通常 256 bit)
          noise_sigma: 雜訊標準差 (σ), 範圍 0.01 ~ 0.20
                      - 0.01 = 1% 位元翻轉 (低雜訊)
                      - 0.05 = 5% 位元翻轉 (中等雜訊) ⭐ 推薦
                      - 0.10 = 10% 位元翻轉 (高雜訊)
                      - 0.20 = 20% 位元翻轉 (極端雜訊)
        """
        self.response_bits = response_bits
        self.noise_sigma = noise_sigma
    
    def validate(self):
        """驗證配置合理性"""
        assert 0.001 <= self.noise_sigma <= 0.50, f"Noise sigma 必须在 0.001~0.50 之間"
        assert self.response_bits > 0, f"Response bits 必须 > 0"


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
        # 1. 將 Hex 轉為二進制整數
        ideal_int = int(ideal_response, 16)
        
        # 2. 計算應翻轉的位元數
        #    使用二項分佈：翻轉的位元數 ~ B(n=256, p=σ)
        num_flips = 0
        for bit_idx in range(self.config.response_bits):
            if random.random() < self.config.noise_sigma:
                num_flips += 1
        
        # 3. 隨機選擇要翻轉的位元索引
        bits_to_flip = random.sample(
            range(self.config.response_bits),
            min(num_flips, self.config.response_bits)
        )
        
        # 4. 執行位元翻轉
        noisy_int = ideal_int
        for bit_idx in bits_to_flip:
            noisy_int ^= (1 << bit_idx)
        
        # 5. 轉回 Hex 字串
        noisy_response = hex(noisy_int)[2:].zfill(64)
        
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
    認證引擎 - 計算 FAR/FRR
    
    FAR = False Accept Rate (誤接受率)
          = Pr(冒充者被接受)
          = 冒充者成功的次數 / 冒充者嘗試總數
    
    FRR = False Rejection Rate (誤拒絕率)
          = Pr(合法用戶被拒絕)
          = 合法用戶失敗的次數 / 合法用戶嘗試總數
    
    EER (Equal Error Rate)
          = FAR = FRR 時的點 (通常用於評估系統性能)
    """
    
    def __init__(self, threshold: int = 40):
        """
        參數：
          threshold: 漢明距離閾值
                    如果 HD ≤ threshold → 接受
                    如果 HD > threshold → 拒絕
        """
        self.threshold = threshold
    
    def authenticate(self, hd: int) -> bool:
        """
        根據漢明距離判定認證結果
        
        返回：
          True = 認證通過，False = 認證失敗
        """
        return hd <= self.threshold
    
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

def generate_challenge(seed: str = None) -> str:
    """生成隨機 Challenge"""
    if seed is None:
        seed = str(time.time())
    challenge = hashlib.sha256(seed.encode()).hexdigest()
    return challenge


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
