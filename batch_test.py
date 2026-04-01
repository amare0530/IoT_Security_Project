"""
═══════════════════════════════════════════════════════════════════
批量測試腳本 - Phase 2 數據生成
Batch Test for FAR/FRR Analysis
═══════════════════════════════════════════════════════════════════

工作流程：
  1. 設置 PUF 模擬器 (高斯雜訊 σ=0.05)
  2. 運行 100 次 「合法用戶」測試
     - Challenge 隨機生成
     - Response 帶雜訊
     - 計算 HD（應較小）
  3. 運行 100 次 「冒充者」測試
     - 使用「陌生」Challenge
     - 計算 HD（應較大）
  4. 在不同門檻下計算 FAR/FRR
  5. 輸出 CSV + 統計報表

預期結果：
  - Genuine HD 分佈: 較小 (平均 ~12-15 bits)
  - Impostor HD 分佈: 較大 (平均 ~125-130 bits)
  - 清晰的分離曲線 → 能畫 ROC 曲線

作者: IoT Security Project - Phase 2
日期: 2026.03.31
"""

import csv
import json
import time
import random
import os
from datetime import datetime
from typing import List, Tuple
import math

# 導入 PUF 模擬器
from puf_simulator import (
    PUFSimulator,
    PUFConfig,
    AuthenticationEngine,
    TestRecord,
    generate_challenge,
    print_stats
)
from config import get_realistic_puf_profile

# ═══════════════════════════════════════════════════════════════
# 【配置】
# ═══════════════════════════════════════════════════════════════

class BatchTestConfig:
    """批量測試配置"""
    
    # 測試參數
    NUM_GENUINE = 100          # 合法用戶測試次數
    NUM_IMPOSTOR = 100         # 冒充者測試次數
    
    # PUF 參數（使用較貼近現場的保守預設，避免過度理想化）
    REALISTIC = get_realistic_puf_profile()
    NOISE_SIGMA = REALISTIC["noise_sigma"]
    BIAS_RATIO = REALISTIC["bias_ratio"]
    BIAS_STRENGTH = REALISTIC["bias_strength"]
    UNSTABLE_RATIO = REALISTIC["unstable_ratio"]
    UNSTABLE_EXTRA_NOISE = REALISTIC["unstable_extra_noise"]
    CLUSTER_NOISE_PROB = REALISTIC["cluster_noise_prob"]
    CLUSTER_SIZE = REALISTIC["cluster_size"]
    ENV_NOISE_SIGMA = REALISTIC["env_noise_sigma"]
    ENV_SPIKE_PROB = REALISTIC["env_spike_prob"]
    ENV_SPIKE_MIN = REALISTIC["env_spike_min"]
    ENV_SPIKE_MAX = REALISTIC["env_spike_max"]
    puf_key = "PUF_DEVICE_UNIQUE_KEY_001"  # 設備唯一密鑰
    
    # 認證參數
    THRESHOLD_RANGE = range(10, 50, 5)  # 測試的閾值範圍 [10, 15, 20, ...]
    
    # 輸出
    OUTPUT_CSV = os.path.join("artifacts", "batch_test_results.csv")
    OUTPUT_REPORT = os.path.join("artifacts", "batch_test_report.json")
    
    # 時間戳印
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")


# ═══════════════════════════════════════════════════════════════
# 【測試執行】
# ═══════════════════════════════════════════════════════════════

class BatchTestExecutor:
    """批量測試執行器"""
    
    def __init__(self, config: BatchTestConfig):
        self.config = config
        
        # 初始化 PUF 模擬器
        puf_config = PUFConfig(
            response_bits=256,
            noise_sigma=config.NOISE_SIGMA,
            bias_ratio=config.BIAS_RATIO,
            bias_strength=config.BIAS_STRENGTH,
            unstable_ratio=config.UNSTABLE_RATIO,
            unstable_extra_noise=config.UNSTABLE_EXTRA_NOISE,
            cluster_noise_prob=config.CLUSTER_NOISE_PROB,
            cluster_size=config.CLUSTER_SIZE,
            env_noise_sigma=config.ENV_NOISE_SIGMA,
            env_spike_prob=config.ENV_SPIKE_PROB,
            env_spike_min=config.ENV_SPIKE_MIN,
            env_spike_max=config.ENV_SPIKE_MAX,
        )
        self.puf = PUFSimulator(config.puf_key, puf_config)
        
        # 記錄存儲
        self.records: List[TestRecord] = []
        self.genuine_hds: List[int] = []
        self.impostor_hds: List[int] = []
    
    def run_genuine_tests(self):
        """
        運行合法用戶測試
        
        場景：
          - 同一設備多次認證
          - 每次 Challenge 不同，但裝置的 PUF 特性相同
          - 因此總應該識別出該設備
        """
        print(f"\n{'='*70}")
        print(f"🟢 開始合法用戶測試 ({self.config.NUM_GENUINE} 次)")
        print(f"{'='*70}")
        
        for i in range(self.config.NUM_GENUINE):
            # 生成新 Challenge
            challenge = generate_challenge(seed=f"genuine_test_{i}_{time.time()}")
            
            # 獲取 PUF 響應（理想 + 雜訊）
            ideal_resp, noisy_resp = self.puf.generate_response(challenge, add_noise=True)
            
            # 計算漢明距離
            # 在現實中，合法設備會使用糾正碼 (Code Error Correction, CCE)
            # 這裡為簡化，假設設備再次讀取相同 Challenge 會產生類似但略有不同的回應
            second_read_resp = self.puf.add_gaussian_noise(ideal_resp)
            hd = self.puf.get_hamming_distance(noisy_resp, second_read_resp)
            
            # 認證
            threshold = 20  # 臨時閾值
            result = hd <= threshold
            
            # 記錄
            record = TestRecord(
                challenge=challenge,
                test_type="genuine",
                ideal_response=ideal_resp,
                noisy_response=noisy_resp,
                hamming_distance=hd,
                threshold=threshold,
                result=result
            )
            self.records.append(record)
            self.genuine_hds.append(hd)
            
            # 進度顯示
            if (i + 1) % 20 == 0:
                avg_hd = sum(self.genuine_hds[-20:]) / 20
                print(f"   進度: {i+1}/{self.config.NUM_GENUINE} | "
                      f"最近 20 次平均 HD: {avg_hd:.2f}")
        
        print(f"✅ 合法用戶測試完成")
        print(f"   總計: {len(self.genuine_hds)} 次")
        print(f"   平均 HD: {sum(self.genuine_hds)/len(self.genuine_hds):.2f}")
        print(f"   範圍: [{min(self.genuine_hds)}, {max(self.genuine_hds)}]")
    
    def run_impostor_tests(self):
        """
        運行冒充者測試
        
        場景：
          - 攻擊者嘗試使用「陌生」Challenge
          - 或者使用完全不同設備的 PUF 特性
          - 期望漢明距離 ~= 128 (隨機相似度)
        """
        print(f"\n{'='*70}")
        print(f"🔴 開始冒充者測試 ({self.config.NUM_IMPOSTOR} 次)")
        print(f"{'='*70}")
        
        # 模擬攻擊者的「偽造」PUF (完全不同的設備)
        fake_puf_key = "ATTACKER_FAKE_PUF_KEY_999"
        fake_puf = PUFSimulator(
            fake_puf_key,
            PUFConfig(
                response_bits=256,
                noise_sigma=self.config.NOISE_SIGMA,
                bias_ratio=self.config.BIAS_RATIO,
                bias_strength=self.config.BIAS_STRENGTH,
                unstable_ratio=self.config.UNSTABLE_RATIO,
                unstable_extra_noise=self.config.UNSTABLE_EXTRA_NOISE,
                cluster_noise_prob=self.config.CLUSTER_NOISE_PROB,
                cluster_size=self.config.CLUSTER_SIZE,
                env_noise_sigma=self.config.ENV_NOISE_SIGMA,
                env_spike_prob=self.config.ENV_SPIKE_PROB,
                env_spike_min=self.config.ENV_SPIKE_MIN,
                env_spike_max=self.config.ENV_SPIKE_MAX,
            ),
        )
        
        for i in range(self.config.NUM_IMPOSTOR):
            # 冒充者使用新 Challenge
            challenge = generate_challenge(seed=f"impostor_test_{i}_{time.time()}")
            
            # 冒充者的響應（完全不同的設備）
            ideal_resp_fake, noisy_resp_fake = fake_puf.generate_response(challenge, add_noise=True)
            
            # 與真實設備的理想響應比較漢明距離
            real_ideal_resp, _ = self.puf.generate_response(challenge, add_noise=False)
            hd = self.puf.get_hamming_distance(real_ideal_resp, noisy_resp_fake)
            
            # 認證
            threshold = 20
            result = hd <= threshold
            
            # 記錄
            record = TestRecord(
                challenge=challenge,
                test_type="impostor",
                ideal_response=real_ideal_resp,
                noisy_response=noisy_resp_fake,
                hamming_distance=hd,
                threshold=threshold,
                result=result
            )
            self.records.append(record)
            self.impostor_hds.append(hd)
            
            # 進度顯示
            if (i + 1) % 20 == 0:
                avg_hd = sum(self.impostor_hds[-20:]) / 20
                print(f"   進度: {i+1}/{self.config.NUM_IMPOSTOR} | "
                      f"最近 20 次平均 HD: {avg_hd:.2f}")
        
        print(f"✅ 冒充者測試完成")
        print(f"   總計: {len(self.impostor_hds)} 次")
        print(f"   平均 HD: {sum(self.impostor_hds)/len(self.impostor_hds):.2f}")
        print(f"   範圍: [{min(self.impostor_hds)}, {max(self.impostor_hds)}]")
    
    def analyze_across_thresholds(self):
        """
        在不同門檻值下分析 FAR/FRR
        
        這會產出一份「ROC 曲線」的數據點
        """
        print(f"\n{'='*70}")
        print(f"📈 跨門檻分析 (ROC 曲線數據生成)")
        print(f"{'='*70}")
        
        analysis_results = []
        
        for threshold in self.config.THRESHOLD_RANGE:
            engine = AuthenticationEngine(threshold)
            metrics = engine.compute_metrics(self.genuine_hds, self.impostor_hds)
            
            analysis_results.append({
                "threshold": threshold,
                "FAR": metrics["FAR"],
                "FRR": metrics["FRR"],
                "accuracy": metrics["accuracy"]
            })
            
            print(f"Threshold={threshold:3d}: "
                  f"FAR={metrics['FAR']:.4f} | "
                  f"FRR={metrics['FRR']:.4f} | "
                  f"Accuracy={metrics['accuracy']:.4f}")
        
        return analysis_results
    
    def export_csv(self):
        """匯出 CSV 報表"""
        csv_path = self.config.OUTPUT_CSV
        os.makedirs(os.path.dirname(csv_path), exist_ok=True)
        
        with open(csv_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=[
                "timestamp", "test_type", "challenge", "ideal_response",
                "noisy_response", "hamming_distance", "threshold", "result"
            ])
            
            writer.writeheader()
            for record in self.records:
                writer.writerow(record.to_dict())
        
        print(f"✅ 已匯出 CSV: {csv_path}")
        return csv_path
    
    def export_report(self, analysis_results: list):
        """匯出 JSON 報表"""
        json_path = self.config.OUTPUT_REPORT
        os.makedirs(os.path.dirname(json_path), exist_ok=True)
        
        report = {
            "timestamp": self.config.timestamp,
            "test_config": {
                "num_genuine": self.config.NUM_GENUINE,
                "num_impostor": self.config.NUM_IMPOSTOR,
                "noise_sigma": self.config.NOISE_SIGMA,
            },
            "statistics": {
                "genuine": {
                    "count": len(self.genuine_hds),
                    "mean_hd": sum(self.genuine_hds) / len(self.genuine_hds) if self.genuine_hds else 0,
                    "min_hd": min(self.genuine_hds) if self.genuine_hds else 0,
                    "max_hd": max(self.genuine_hds) if self.genuine_hds else 0,
                    "std_dev": self._std_dev(self.genuine_hds) if self.genuine_hds else 0,
                },
                "impostor": {
                    "count": len(self.impostor_hds),
                    "mean_hd": sum(self.impostor_hds) / len(self.impostor_hds) if self.impostor_hds else 0,
                    "min_hd": min(self.impostor_hds) if self.impostor_hds else 0,
                    "max_hd": max(self.impostor_hds) if self.impostor_hds else 0,
                    "std_dev": self._std_dev(self.impostor_hds) if self.impostor_hds else 0,
                }
            },
            "roc_curve_data": analysis_results,
            "all_records": [r.to_dict() for r in self.records]
        }
        
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        print(f"✅ 已匯出 JSON: {json_path}")
        return json_path
    
    @staticmethod
    def _std_dev(values: list) -> float:
        """計算標準差"""
        if len(values) < 2:
            return 0.0
        mean = sum(values) / len(values)
        variance = sum((x - mean) ** 2 for x in values) / (len(values) - 1)
        return math.sqrt(variance)


# ═══════════════════════════════════════════════════════════════
# 【主程式】
# ═══════════════════════════════════════════════════════════════

def main():
    """主測試流程"""
    
    print(f"\n{'='*70}")
    print(f"🚀 Phase 2: 批量測試 - FAR/FRR 數據生成")
    print(f"{'='*70}")
    print(f"開始時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"配置:")
    print(f"  - 合法用戶測試次數: {BatchTestConfig.NUM_GENUINE}")
    print(f"  - 冒充者測試次數: {BatchTestConfig.NUM_IMPOSTOR}")
    print(f"  - 雜訊強度 (σ): {BatchTestConfig.NOISE_SIGMA}")
    
    # 初始化執行器
    executor = BatchTestExecutor(BatchTestConfig())
    
    # Step 1: 運行合法用戶測試
    start_time = time.time()
    executor.run_genuine_tests()
    genuine_time = time.time() - start_time
    
    # Step 2: 運行冒充者測試
    start_time = time.time()
    executor.run_impostor_tests()
    impostor_time = time.time() - start_time
    
    # Step 3: 分析不同門檻
    analysis_results = executor.analyze_across_thresholds()
    
    # Step 4: 匯出結果
    csv_path = executor.export_csv()
    json_path = executor.export_report(analysis_results)
    
    # 最終統計
    print(f"\n{'='*70}")
    print(f"✅ 測試完成")
    print(f"{'='*70}")
    print(f"執行時間:")
    print(f"  - 合法用戶測試: {genuine_time:.2f}s")
    print(f"  - 冒充者測試: {impostor_time:.2f}s")
    print(f"  - 總計: {genuine_time + impostor_time:.2f}s")
    print(f"\n輸出文件:")
    print(f"  📊 CSV: {csv_path}")
    print(f"  📋 JSON: {json_path}")
    print(f"\n下一步:")
    print(f"  1. 用 Python/Excel 讀取 CSV，畫 ROC 曲線")
    print(f"  2. 調整 NOISE_SIGMA 進行敏感度分析")
    print(f"  3. 找出 EER (Equal Error Rate) 點")
    print(f"\n{'='*70}\n")


if __name__ == "__main__":
    main()
