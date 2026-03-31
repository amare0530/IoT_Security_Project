"""
═══════════════════════════════════════════════════════════════════
敏感度分析工具 - 測試不同雜訊強度遞增的影響
Sensitivity Analysis: Noise Level vs FAR/FRR
═══════════════════════════════════════════════════════════════════

目的：
  驗證系統在不同雜訊環境下的魯棒性
  
實驗設計：
  - 執行多輪批量測試，每輪使用不同的 σ (雜訊強度)
  - 計算每輪的 EER、Accuracy、Separation
  - 繪製雜訊強度 vs 性能 的曲線
  
應用場景：
  1. 溫度變化 → 雜訊增加
  2. 老化環境 → 製程變異增加
  3. 惡劣條件 → 干擾增加

科學意義：
  展示系統在真實環境變化下的適應性

作者: IoT Security Project - Phase 2
日期: 2026.03.31
"""

import csv
import json
import time
import os
from typing import Dict, List
import math

from puf_simulator import (
    PUFSimulator,
    PUFConfig,
    AuthenticationEngine,
    generate_challenge
)

# ═══════════════════════════════════════════════════════════════
# 【配置】
# ═══════════════════════════════════════════════════════════════

class SensitivityTestConfig:
    """敏感度測試配置"""
    
    # 測試的雜訊強度範圍
    NOISE_LEVELS = [0.01, 0.03, 0.05, 0.08, 0.10, 0.15, 0.20]  # 1% ~ 20%
    
    # 每個雜訊強度下的重複次數
    NUM_REPEATS_PER_SIGMA = 5  # 為了快速演示，每個 σ 執行 5 次
    
    # 單次測試的大小
    NUM_GENUINE = 100
    NUM_IMPOSTOR = 100
    
    # PUF 配置
    puf_key = "PUF_DEVICE_UNIQUE_KEY_001"
    
    # 認證參數
    THRESHOLD = 35  # 固定閾值用於比較
    
    # 輸出
    OUTPUT_CSV = os.path.join("artifacts", "sensitivity_analysis.csv")
    OUTPUT_JSON = os.path.join("artifacts", "sensitivity_analysis.json")


# ═══════════════════════════════════════════════════════════════
# 【敏感度測試執行器】
# ═══════════════════════════════════════════════════════════════

class SensitivityTestExecutor:
    """敏感度測試執行器"""
    
    def __init__(self, config: SensitivityTestConfig):
        self.config = config
        self.results = []  # 存儲所有結果
    
    def run_single_test(self, sigma: float) -> Dict:
        """
        執行單次測試
        
        參數：
          sigma: 雜訊強度
        
        返回：
          包含 FAR, FRR, EER 等的結果字典
        """
        # 初始化 PUF
        puf_config = PUFConfig(response_bits=256, noise_sigma=sigma)
        puf = PUFSimulator(self.config.puf_key, puf_config)
        
        # 合法用戶測試
        genuine_hds = []
        for i in range(self.config.NUM_GENUINE):
            challenge = generate_challenge(seed=f"gen_{sigma}_{i}_{time.time()}")
            ideal_resp, noisy_resp = puf.generate_response(challenge, add_noise=True)
            second_read = puf.add_gaussian_noise(ideal_resp)
            hd = puf.get_hamming_distance(noisy_resp, second_read)
            genuine_hds.append(hd)
        
        # 冒充者測試
        impostor_hds = []
        fake_puf = PUFSimulator("FAKE_KEY", puf_config)
        for i in range(self.config.NUM_IMPOSTOR):
            challenge = generate_challenge(seed=f"imp_{sigma}_{i}_{time.time()}")
            real_ideal, _ = puf.generate_response(challenge, add_noise=False)
            _, fake_noisy = fake_puf.generate_response(challenge, add_noise=True)
            hd = puf.get_hamming_distance(real_ideal, fake_noisy)
            impostor_hds.append(hd)
        
        # 計算 FAR/FRR
        engine = AuthenticationEngine(self.config.THRESHOLD)
        metrics = engine.compute_metrics(genuine_hds, impostor_hds)
        
        # 計算 EER
        all_hds = genuine_hds + impostor_hds
        
        return {
            "sigma": sigma,
            "genuine_mean": sum(genuine_hds) / len(genuine_hds),
            "genuine_std": self._std_dev(genuine_hds),
            "impostor_mean": sum(impostor_hds) / len(impostor_hds),
            "impostor_std": self._std_dev(impostor_hds),
            "separation": abs(sum(impostor_hds)/len(impostor_hds) - sum(genuine_hds)/len(genuine_hds)),
            "FAR": metrics["FAR"],
            "FRR": metrics["FRR"],
            "accuracy": metrics["accuracy"],
            "EER": (metrics["FAR"] + metrics["FRR"]) / 2,
        }
    
    def run_all_tests(self):
        """執行所有敏感度測試"""
        print(f"\n{'='*80}")
        print(f"🧪 開始敏感度分析測試")
        print(f"{'='*80}")
        print(f"配置:")
        print(f"  - 雜訊強度範圍: {self.config.NOISE_LEVELS}")
        print(f"  - 每個雜訊強度重複: {self.config.NUM_REPEATS_PER_SIGMA} 次")
        print(f"  - 單次測試規模: {self.config.NUM_GENUINE} genuine + {self.config.NUM_IMPOSTOR} impostor")
        print(f"{'='*80}\n")
        
        for sigma in self.config.NOISE_LEVELS:
            print(f"\n🔬 測試 σ = {sigma:.3f} ({int(sigma*100)}% 位元翻轉)")
            print(f"{'-'*80}")
            
            sigma_results = []
            for repeat in range(self.config.NUM_REPEATS_PER_SIGMA):
                result = self.run_single_test(sigma)
                sigma_results.append(result)
                
                print(f"  重複 {repeat+1}/{self.config.NUM_REPEATS_PER_SIGMA}:")
                print(f"    Genuine HD: {result['genuine_mean']:.2f} ± {result['genuine_std']:.2f}")
                print(f"    Impostor HD: {result['impostor_mean']:.2f} ± {result['impostor_std']:.2f}")
                print(f"    Separation: {result['separation']:.2f} bits")
                print(f"    FAR: {result['FAR']:.4f}, FRR: {result['FRR']:.4f}, EER: {result['EER']:.4f}")
            
            # 計算平均值
            avg_result = {
                "sigma": sigma,
                "genuine_mean_avg": sum(r['genuine_mean'] for r in sigma_results) / len(sigma_results),
                "genuine_std_avg": sum(r['genuine_std'] for r in sigma_results) / len(sigma_results),
                "impostor_mean_avg": sum(r['impostor_mean'] for r in sigma_results) / len(sigma_results),
                "impostor_std_avg": sum(r['impostor_std'] for r in sigma_results) / len(sigma_results),
                "separation_avg": sum(r['separation'] for r in sigma_results) / len(sigma_results),
                "FAR_avg": sum(r['FAR'] for r in sigma_results) / len(sigma_results),
                "FRR_avg": sum(r['FRR'] for r in sigma_results) / len(sigma_results),
                "accuracy_avg": sum(r['accuracy'] for r in sigma_results) / len(sigma_results),
                "EER_avg": sum(r['EER'] for r in sigma_results) / len(sigma_results),
            }
            
            self.results.append(avg_result)
            
            print(f"  平均結果:")
            print(f"    Separation: {avg_result['separation_avg']:.2f} bits")
            print(f"    FAR: {avg_result['FAR_avg']:.4f}, FRR: {avg_result['FRR_avg']:.4f}")
            print(f"    Accuracy: {avg_result['accuracy_avg']:.4f}, EER: {avg_result['EER_avg']:.4f}")
        
        print(f"\n{'='*80}")
        print(f"✅ 所有敏感度測試完成")
        print(f"{'='*80}\n")
    
    def export_results(self):
        """匯出結果"""
        output_dir = os.path.dirname(self.config.OUTPUT_CSV)
        os.makedirs(output_dir, exist_ok=True)

        # CSV
        with open(self.config.OUTPUT_CSV, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=[
                "sigma", "genuine_mean_avg", "genuine_std_avg",
                "impostor_mean_avg", "impostor_std_avg", "separation_avg",
                "FAR_avg", "FRR_avg", "accuracy_avg", "EER_avg"
            ])
            writer.writeheader()
            writer.writerows(self.results)
        
        print(f"✅ 已匯出 CSV: {self.config.OUTPUT_CSV}")
        
        # JSON
        with open(self.config.OUTPUT_JSON, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, indent=2, ensure_ascii=False)
        
        print(f"✅ 已匯出 JSON: {self.config.OUTPUT_JSON}")
    
    def print_summary(self):
        """列印摘要"""
        print(f"\n{'='*80}")
        print(f"📊 敏感度分析摘要")
        print(f"{'='*80}")
        print(f"{'σ (Noise)':<15} {'Separation':<15} {'Accuracy':<12} {'EER':<12} {'Eval'}")
        print(f"{'-'*80}")
        
        for r in self.results:
            sigma = r['sigma']
            sep = r['separation_avg']
            acc = r['accuracy_avg']
            eer = r['EER_avg']
            
            # 評級
            if sep > 50 and acc > 0.95:
                eval_str = "⭐⭐⭐ 優秀"
            elif sep > 30 and acc > 0.90:
                eval_str = "⭐⭐ 良好"
            elif sep > 20 and acc > 0.80:
                eval_str = "⭐ 可接受"
            else:
                eval_str = "❌ 不可接受"
            
            print(f"{sigma:<15.3f} {sep:<15.2f} {acc:<12.4f} {eer:<12.4f} {eval_str}")
        
        print(f"{'='*80}")
        
        # 建議
        print(f"\n💡 建議:")
        best_result = max(self.results, key=lambda x: x['accuracy_avg'])
        print(f"  - 最優雜訊強度: σ = {best_result['sigma']:.3f}")
        print(f"  - 此時精度: {best_result['accuracy_avg']:.4f}")
        
        # 找出「可接受的最大雜訊」
        acceptable = [r for r in self.results if r['accuracy_avg'] > 0.90]
        if acceptable:
            max_acceptable = max(acceptable, key=lambda x: x['sigma'])
            print(f"  - 精度 > 90% 的最大雜訊: σ = {max_acceptable['sigma']:.3f}")
        
        print()
    
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
    """主流程"""
    config = SensitivityTestConfig()
    executor = SensitivityTestExecutor(config)
    
    # 執行測試
    executor.run_all_tests()
    
    # 匯出結果
    executor.export_results()
    
    # 列印摘要
    executor.print_summary()


if __name__ == "__main__":
    main()
