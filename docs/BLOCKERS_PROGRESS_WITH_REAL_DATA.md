# 五個技術阻塞器進度 - 使用真實 Zenodo 資料 (2026-04-07)

已取得 **84 設備，924 筆感測器記錄** 的真實 Zenodo TIMA 資料。

## 進度總表

| # | 阻塞器 | 完成度 | 狀態 | 關鍵發現 |
|---|--------|--------|------|----------|
| 1 | 響應資料完整性 (512 bytes) | 30% | ⏳ CRP 資料待入手 | sensors 已導入；CRP 120k 列未下載 |
| 2 | Challenge 多樣性 (160 地址/設備) | 5% | ⏳ 等 CRP 資料 | sensors 只有 temp/voltage，非 address |
| 3 | ECC 實現需求 | 40% | ✓ 初步評估 | 溫度範圍 10x 寬，可能需要 ECC |
| 4 | 群體規模測試 (N=84) | 50% | ✓ 資料備妥 | 84 設備 11 採樣數，統計準備完成 |
| 5 | Margin 驗證 (87 bits) | 10% | ✗ BLOCKED | 溫度 9-34°C，未驗證上限值 |

**整體進度: 27% 完成，73% 待測**

---

## 阻塞器 1: 響應資料完整性

**問題**: Zenodo 聲稱每個記錄是 512 bytes，但未驗證

### 現況
- ✓ sensors.csv (925 筆）已導入
- ✗ crp_data*.csv (120,961 筆) 尚未取得

### 待做
```bash
# 下載完整 CRP 資料集（~50MB）
# 然後驗證每筆記錄是否真的 512 bytes
python -c "
import csv
with open('zenodo_crp_data.csv', 'r') as f:
    reader = csv.DictReader(f)
    for i, row in enumerate(reader):
        data = row['data'].split(',')
        if len(data) != 512:
            print(f'ROW {i}: Expected 512 bytes, got {len(data)}')
            break
    if i % 10000 == 0:
        print(f'✓ Verified {i} records...')
"
```

**依賴**: 無法進行 challenge diversity 分析直到此項完成

---

## 阻塞器 2: Challenge 多樣性

**問題**: 每個設備是否真的有 160 個不同的位址？

### 現況
- sensors.csv 只有 temperature/voltage，無 address
- **下一步**: 從 crp_data.csv 中抽樣，計算每設備的獨特地址數

### 預期結果
```
需要驗證:
- 每設備 ≥ 160 個不同位址 ✓/✗
- 位址是否均勻分布 (0x20000000 - 0x20027FFF) ✓/✗
- 是否存在『熱點地址』(某些位址重複採樣) ✓/✗
```

### 風險
- 如果 < 160 個位址: Challenge 空間受限，diversity 低
- 如果位址非均勻: 可能導致某些區域 PUF 更弱

**優先級**: HIGH (直接影響 Margin)

---

## 阻塞器 3: ECC 實現需求 (✓ 初步評估完成)

**發現**: 真實環境比 Phase 1 嚴苛

### 溫度分析結果
```
Phase 1 假設: ±2-3°C (20-25°C)
Zenodo 實測:
  - 最低: 9.33°C    (-11°C vs Phase 1)
  - 最高: 34.11°C   (+9°C vs Phase 1)
  - 范圍: 24.79°C   (10x 更寬)
```

### 電壓分析結果
```
Phase 1 假設: 3.3V ± 5% (3.135-3.465V)
Zenodo 實測:
  - 最低: 3.46987V  (正常)
  - 最高: 3.67130V  (過上限！ > 3.6V)
  - 存在過壓狀況，可能增加位元翻轉
```

### ECC 決策 (待驗證)
```
如果 BER > 10% in extreme conditions:
  → 需要 Hamming(512, 487) 或 BCH
  → 成本: ~1ms 認證延遲 + 儲存開銷

如果 BER < 5%:
  → 可能不需要 ECC，只需更寬的門檻範圍
```

**下一步**: 用真實 CRP 資料計算極端條件下的 BER

---

## 阻塞器 4: 群體規模測試 (N=84) (✓ 50% 完成)

**進度**: 資料已備妥，統計工具準備完成

### 已驗證
```
✓ 84 個唯一設備 UID
✓ 11 次採樣 × 84 設備 = 924 筆記錄
✓ 溫度和電壓都有記錄
✓ 時間跨度 10 週 (2022-11-14 ~ 2023-01-23)
```

### 待做
```bash
# 計算群體統計
python population_statistics.py \
  --input artifacts/zenodo_sensors.db \
  --devices 84 \
  --output artifacts/zenodo_population_stats.json

# 預期輸出:
# - 溫度分布 (平均、分位數、異常值)
# - 電壓分布 (平均、分位數、異常值)
# - 設備間的溫度差異 (inter-device variation)
# - 設備間的電壓差異 (inter-device variation)
```

**風險**: FAR 會隨著 N 增加而上升
```
N=5 (Phase 1):   FAR 未知
N=84 (Zenodo):   FAR = ?

Coupon Collector Problem:
假設每對設備有 1% 的重疊風險
- N=5: 總風險 ~ 0.05%
- N=84: 總風險 ~ 0.7%

需要實測驗證此估計
```

**優先級**: HIGH (決定系統是否可用於生產)

---

## 阻塞器 5: Margin 驗證 (87 bits) (✓ 10% 完成)

**當前聲稱**: Margin = 87 bits (未指定條件)

### 問題
```
✗ 在哪溫度下? (9°C? 34°C? 平均 16.6°C?)
✗ 在哪電壓下? (3.47V? 3.67V? 平均 3.65V?)
✗ N 多少? (5? 84?)
✗ 如何定義 margin? (直接計算 min inter-device distance?)
```

### 待驗證
```
套用公式:
  Margin (bits) = min(inter-device HD) - 3*std(intra-device HD)

在不同環境下計算:
  - 9°C: Margin = ?
  - 16.6°C: Margin = ?
  - 34°C: Margin = ?

預期結果 (假設):
  - 16.6°C: Margin = 87 bits (符合聲稱)
  - 9°C: Margin = 92 bits (更好)
  - 34°C: Margin = 45 bits (惡化 48% !!!)
```

如果上述預測成立 → **需要 ECC 支持 34°C 場景**

---

## 實命行動計劃 (本週)

### TODAY (已完成)
- ✓ 導入 sensors.csv (924 筆記錄)
- ✓ 分析溫度/電壓統計
- ✓ 識別環境異常 (過壓、極端溫度)

### Tomorrow (下一步)
1. 下載 CRP 資料 (crp_data.csv)
2. 驗證每筆 512 bytes 完整性
3. 計算每設備的 address 多樣性

### This Week
1. 從真實 CRP 資料計算 inter-device Hamming distance
2. 在極端溫度下測試 margin 退化
3. 計算 population-scale FAR @ N=84

### Decision Point (End of Week)
```
IF Margin @ 34°C < 50 bits:
  → 立即實裝 ECC
  → 修改答辯簡報 (承認限制)

IF Margin @ 34°C ≥ 50 bits:
  → 保留 87 bits 聲稱，但加註條件
  → 建議使用環境恆溫控制

IF FAR @ N=84 > 10^-4:
  → 無法用於生產 84 設備場景
  → 需要多因子驗證或設備限制
```

---

## 量化目標 (向答辯時可交付的成果)

| 交付物 | 現況 | 目標 | 期限 |
|--------|------|------|------|
| 真實資料導入 | 60% | 100% (CRP + sensors) | 明日 |
| Margin vs Temperature 圖表 | 0% | 完整曲線 | 本週 |
| Population-scale FAR 表格 | 0% | N=5,10,20,50,84 | 本週 |
| ECC 需求評估 | 初步 | 明確決議 | 本週五 |
| 更新答辯簡報 | 舊版聲稱 | 證據支持版 | 下週 |

---

**核心訊息**: 有真實資料了。現在要用數據說話，不是用聲稱。
