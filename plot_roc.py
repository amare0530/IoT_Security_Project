"""
═══════════════════════════════════════════════════════════════════
ROC 曲線與 EER 分析工具
ROC Curve & Equal Error Rate (EER) Visualization
═══════════════════════════════════════════════════════════════════

工作流程：
  1. 讀取 batch_test_report.json
  2. 提取 ROC 曲線數據點
  3. 繪製 FAR vs FRR 圖
  4. 計算並標註 EER (Equal Error Rate)
  5. 生成出版級別的圖表

理論背景：
  ROC 曲線 (Receiver Operating Characteristic):
    - X 軸: FAR (False Accept Rate) - 冒充者被接受的比例
    - Y 軸: 1-FRR (Genuine Accept Rate) - 合法用戶被接受的比例
    - 理想點: (0, 1) - 完全分離
  
  EER (Equal Error Rate):
    - FAR = FRR 時的點
    - 系統性能的單一指標
    - EER 越小越好

使用方式：
  python plot_roc.py [--sigma 0.05] [--show-plot]

依賴：
  - matplotlib: pip install matplotlib
  - numpy: pip install numpy

作者: IoT Security Project - Phase 2
日期: 2026.03.31
"""

import json
import argparse
import sys
from typing import List, Tuple, Dict
import math

# 檢查依賴
try:
    import matplotlib.pyplot as plt
    import numpy as np
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False
    print("⚠️  警告: matplotlib 未安裝")
    print("   執行: pip install matplotlib")


# ═══════════════════════════════════════════════════════════════
# 【數據讀取與處理】
# ═══════════════════════════════════════════════════════════════

class ROCAnalyzer:
    """ROC 曲線分析器"""
    
    def __init__(self, json_report_path: str = "batch_test_report.json"):
        """
        初始化分析器
        
        參數：
          json_report_path: batch_test 輸出的 JSON 報表路徑
        """
        self.json_path = json_report_path
        self.report = None
        self.roc_points = []
        self.eer_point = None
        self.best_threshold = None
        
        # 讀取報表
        self._load_report()
    
    def _load_report(self):
        """讀取 JSON 報表"""
        try:
            with open(self.json_path, 'r', encoding='utf-8') as f:
                self.report = json.load(f)
            print(f"✅ 已讀取報表: {self.json_path}")
        except FileNotFoundError:
            print(f"❌ 找不到報表文件: {self.json_path}")
            sys.exit(1)
        except json.JSONDecodeError:
            print(f"❌ JSON 解析失敗: {self.json_path}")
            sys.exit(1)
    
    def extract_roc_points(self) -> List[Dict]:
        """
        提取 ROC 曲線數據點
        
        返回：
          ROC 點列表 [
            {"threshold": 10, "FAR": 0.0, "FRR": 1.0, "1-FRR": 0.0},
            ...
          ]
        """
        if not self.report:
            return []
        
        roc_data = self.report.get("roc_curve_data", [])
        
        for point in roc_data:
            self.roc_points.append({
                "threshold": point["threshold"],
                "FAR": float(point["FAR"]),
                "FRR": float(point["FRR"]),
                "1-FRR": 1.0 - float(point["FRR"]),
                "accuracy": float(point["accuracy"])
            })
        
        print(f"✅ 提取 {len(self.roc_points)} 個 ROC 數據點")
        return self.roc_points
    
    def find_eer(self) -> Dict:
        """
        計算 EER (Equal Error Rate)
        
        EER = 最接近 FAR = FRR 的點
        """
        if not self.roc_points:
            self.extract_roc_points()
        
        min_diff = float('inf')
        eer_point = None
        
        for point in self.roc_points:
            diff = abs(point["FAR"] - point["FRR"])
            if diff < min_diff:
                min_diff = diff
                eer_point = point
        
        self.eer_point = eer_point
        
        if eer_point:
            print(f"✅ EER 點:")
            print(f"   Threshold: {eer_point['threshold']}")
            print(f"   FAR: {eer_point['FAR']:.4f}")
            print(f"   FRR: {eer_point['FRR']:.4f}")
            print(f"   |FAR - FRR|: {abs(eer_point['FAR'] - eer_point['FRR']):.4f}")
            print(f"   EER ≈ {(eer_point['FAR'] + eer_point['FRR'])/2:.4f}")
        
        return eer_point
    
    def find_best_threshold(self, metric: str = "accuracy") -> Dict:
        """
        找最佳閾值
        
        參數：
          metric: 優化指標 ("accuracy", "FAR", "FRR")
        """
        if not self.roc_points:
            self.extract_roc_points()
        
        if metric == "accuracy":
            best = max(self.roc_points, key=lambda x: x["accuracy"])
        elif metric == "FAR":
            best = min(self.roc_points, key=lambda x: x["FAR"])
        elif metric == "FRR":
            best = min(self.roc_points, key=lambda x: x["FRR"])
        else:
            raise ValueError(f"未知的 metric: {metric}")
        
        self.best_threshold = best
        
        print(f"✅ 最佳閾值 (基於 {metric}):")
        print(f"   Threshold: {best['threshold']}")
        print(f"   FAR: {best['FAR']:.4f}")
        print(f"   FRR: {best['FRR']:.4f}")
        print(f"   Accuracy: {best['accuracy']:.4f}")
        
        return best
    
    def print_statistics(self):
        """列印統計信息"""
        if not self.report:
            return
        
        stats = self.report.get("statistics", {})
        genuine = stats.get("genuine", {})
        impostor = stats.get("impostor", {})
        
        print(f"\n{'='*70}")
        print(f"📊 測試統計")
        print(f"{'='*70}")
        print(f"✅ 合法用戶 (Genuine):")
        print(f"   計數: {genuine.get('count', 0)}")
        print(f"   平均 HD: {genuine.get('mean_hd', 0):.2f}")
        print(f"   標準差: {genuine.get('std_dev', 0):.2f}")
        print(f"   範圍: [{genuine.get('min_hd', 0)}, {genuine.get('max_hd', 0)}]")
        
        print(f"\n❌ 冒充者 (Impostor):")
        print(f"   計數: {impostor.get('count', 0)}")
        print(f"   平均 HD: {impostor.get('mean_hd', 0):.2f}")
        print(f"   標準差: {impostor.get('std_dev', 0):.2f}")
        print(f"   範圍: [{impostor.get('min_hd', 0)}, {impostor.get('max_hd', 0)}]")
        
        print(f"\n📈 分離度 (Separability):")
        genuine_mean = genuine.get('mean_hd', 0)
        impostor_mean = impostor.get('mean_hd', 0)
        separation = abs(impostor_mean - genuine_mean)
        print(f"   HD 差: {separation:.2f} bits")
        print(f"   倍數: {impostor_mean/genuine_mean:.2f}x")
        if separation > 50:
            print(f"   評級: ⭐⭐⭐ 優秀 (分離度 > 50)")
        elif separation > 20:
            print(f"   評級: ⭐⭐ 良好 (分離度 > 20)")
        else:
            print(f"   評級: ⭐ 一般 (分離度 < 20)")
        
        print(f"{'='*70}\n")


# ═══════════════════════════════════════════════════════════════
# 【繪圖函數】
# ═══════════════════════════════════════════════════════════════

def plot_roc_curve(analyzer: ROCAnalyzer, output_path: str = "roc_curve.png"):
    """
    繪製 ROC 曲線
    
    參數：
      analyzer: ROCAnalyzer 對象
      output_path: 輸出圖片路徑
    """
    if not HAS_MATPLOTLIB:
        print("⚠️  無法繪製圖表（matplotlib 未安裝）")
        print("   執行: pip install matplotlib")
        return
    
    roc_points = analyzer.roc_points
    if not roc_points:
        roc_points = analyzer.extract_roc_points()
    
    # 提取數據
    fars = [p["FAR"] for p in roc_points]
    frs = [p["1-FRR"] for p in roc_points]
    thresholds = [p["threshold"] for p in roc_points]
    
    # 建立圖表
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    
    # ── 圖 1: ROC 曲線 ──
    ax1 = axes[0]
    ax1.plot(fars, frs, 'b-o', linewidth=2, markersize=6, label='ROC Curve')
    ax1.plot([0, 1], [0, 1], 'r--', linewidth=1, label='Random')
    
    # 標註 EER 點
    if analyzer.eer_point:
        eer_FAR = analyzer.eer_point["FAR"]
        eer_FR = analyzer.eer_point["1-FRR"]
        ax1.plot(eer_FAR, eer_FR, 'go', markersize=10, label=f"EER (T={analyzer.eer_point['threshold']})")
    
    # 標註最佳點
    if analyzer.best_threshold:
        best_FAR = analyzer.best_threshold["FAR"]
        best_FR = analyzer.best_threshold["1-FRR"]
        ax1.plot(best_FAR, best_FR, 'r*', markersize=15, label=f"Best (T={analyzer.best_threshold['threshold']})")
    
    # 標註每個點的閾值
    for i, (far, fr, th) in enumerate(zip(fars, frs, thresholds)):
        if i % 2 == 0:  # 隔一個點標註，避免擁擠
            ax1.annotate(f'T={th}', (far, fr), fontsize=8, alpha=0.7)
    
    ax1.set_xlabel('FAR (False Accept Rate)', fontsize=11)
    ax1.set_ylabel('FRR (Genuine Accept Rate)', fontsize=11)
    ax1.set_title('ROC Curve - Trade-off Analysis', fontsize=12, fontweight='bold')
    ax1.grid(True, alpha=0.3)
    ax1.legend(loc='best')
    ax1.set_xlim([-0.05, 1.05])
    ax1.set_ylim([-0.05, 1.05])
    
    # ── 圖 2: FAR vs FRR vs Threshold ──
    ax2 = axes[1]
    ax2.plot(thresholds, fars, 'r-o', linewidth=2, markersize=6, label='FAR')
    ax2.plot(thresholds, [p["FRR"] for p in roc_points], 'b-s', linewidth=2, markersize=6, label='FRR')
    
    # 標註 EER 點
    if analyzer.eer_point:
        th = analyzer.eer_point["threshold"]
        far = analyzer.eer_point["FAR"]
        ax2.plot(th, far, 'go', markersize=10)
    
    ax2.set_xlabel('Threshold', fontsize=11)
    ax2.set_ylabel('Error Rate', fontsize=11)
    ax2.set_title('FAR & FRR vs Threshold', fontsize=12, fontweight='bold')
    ax2.grid(True, alpha=0.3)
    ax2.legend(loc='best')
    ax2.set_ylim([-0.05, 1.05])
    
    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"✅ 已保存圖表: {output_path}")
    
    return fig


def print_roc_table(analyzer: ROCAnalyzer):
    """列印 ROC 數據表"""
    print(f"\n{'='*70}")
    print(f"📊 ROC 曲線數據表")
    print(f"{'='*70}")
    print(f"{'Threshold':<12} {'FAR':<12} {'FRR':<12} {'1-FRR':<12} {'Accuracy':<12}")
    print(f"{'-'*70}")
    
    for point in analyzer.roc_points:
        print(f"{point['threshold']:<12} "
              f"{point['FAR']:<12.4f} "
              f"{point['FRR']:<12.4f} "
              f"{point['1-FRR']:<12.4f} "
              f"{point['accuracy']:<12.4f}")
    
    print(f"{'='*70}\n")


# ═══════════════════════════════════════════════════════════════
# 【主程式】
# ═══════════════════════════════════════════════════════════════

def main():
    """主分析流程"""
    
    parser = argparse.ArgumentParser(
        description="ROC 曲線分析工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例：
  python plot_roc.py                          # 基本分析
  python plot_roc.py --show-plot              # 顯示圖表
  python plot_roc.py --json other_report.json # 讀取其他報表
        """
    )
    parser.add_argument('--json', default='batch_test_report.json',
                       help='JSON 報表路徑 (預設: batch_test_report.json)')
    parser.add_argument('--output', default='roc_curve.png',
                       help='輸出圖片路徑 (預設: roc_curve.png)')
    parser.add_argument('--show-plot', action='store_true',
                       help='顯示交互式圖表')
    parser.add_argument('--table', action='store_true',
                       help='列印數據表')
    
    args = parser.parse_args()
    
    print(f"\n{'='*70}")
    print(f"📈 ROC 曲線分析工具")
    print(f"{'='*70}")
    
    # 初始化分析器
    analyzer = ROCAnalyzer(args.json)
    
    # 提取 ROC 點
    analyzer.extract_roc_points()
    
    # 列印統計信息
    analyzer.print_statistics()
    
    # 計算 EER 和最佳閾值
    analyzer.find_eer()
    print()
    analyzer.find_best_threshold()
    
    # 列印數據表
    if args.table:
        print_roc_table(analyzer)
    
    # 繪製圖表
    if HAS_MATPLOTLIB:
        plot_roc_curve(analyzer, args.output)
        
        if args.show_plot:
            print("\n🖼️  顯示交互式圖表...")
            plt.show()
    
    print(f"\n{'='*70}")
    print(f"✅ 分析完成")
    print(f"{'='*70}\n")


if __name__ == "__main__":
    main()
