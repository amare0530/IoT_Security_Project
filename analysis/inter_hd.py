import matplotlib.pyplot as plt
import seaborn as sns
from itertools import permutations
from pathlib import Path
import numpy as np
import pandas as pd
import json

def compute_and_plot_inter_hd(masks_path, stability_csv, threshold=0.9):
    # 1. 讀取數據
    with open(masks_path) as f:
        masks = json.load(f)
    
    selected_bits = {
        m["uid"]: np.array(list(m["mask"]), dtype=np.uint8)
        for m in masks if m["threshold"] == threshold
    }

    print("讀取 stability_summary.csv...")
    stab = pd.read_csv(stability_csv, low_memory=False)
    
    dominant = {}
    for uid, group in stab.groupby("uid"):
        arr = group.sort_values("bit_position")["dominant_bit"].to_numpy(dtype=np.uint8)
        dominant[uid] = arr

    # 2. 計算 0/1 比例 (Hamming Weight)
    all_bits = np.concatenate(list(dominant.values()))
    hw = np.mean(all_bits)
    print(f"物理偏誤分析: 0 佔 {1-hw:.4f}, 1 佔 {hw:.4f}")

    # 3. 計算 Inter-HD (Permutations)
    uids = list(selected_bits.keys())
    hd_values = []
    
    for uid_a, uid_b in permutations(uids, 2):
        if uid_a not in dominant or uid_b not in dominant: continue
        
        mask_a = selected_bits[uid_a].astype(bool)
        dom_a = dominant[uid_a][mask_a]
        dom_b = dominant[uid_b][mask_a]
        
        hd = np.mean(dom_a != dom_b)
        hd_values.append(hd)

    # 4. 繪製 Inter-HD 分佈圖
    plt.figure(figsize=(10, 6))
    sns.histplot(hd_values, kde=True, color='skyblue', bins=30)
    plt.axvline(x=0.5, color='red', linestyle='--', label='Ideal (0.5)')
    plt.axvline(x=np.mean(hd_values), color='green', linestyle='-', label=f'Mean ({np.mean(hd_values):.4f})')
    
    plt.title("Inter-device Hamming Distance Distribution")
    plt.xlabel("Hamming Distance")
    plt.ylabel("Frequency")
    plt.legend()
    plt.grid(axis='y', alpha=0.3)
    
    # 確保資料夾存在並存檔
    Path("artifacts").mkdir(exist_ok=True)
    plt.savefig("artifacts/inter_hd_dist.png")
    print(f"分佈圖已儲存至 artifacts/inter_hd_dist.png")
    
    return pd.DataFrame({"inter_hd": hd_values})

if __name__ == "__main__":
    df = compute_and_plot_inter_hd(
        Path("artifacts/masks.json"), 
        Path("artifacts/stability_summary.csv")
    )
    print(f"平均 Inter-HD: {df['inter_hd'].mean():.4f}")