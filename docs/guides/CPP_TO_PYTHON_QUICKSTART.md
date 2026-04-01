# C++ 轉 Python 快速導覽（針對本專案）

這份文件給「會 C++、剛接觸 Python」的你。

目標：不用先學完整 Python，也能讀懂並修改這個專案。

## 先記 6 個對照

1. C++ 的 `#include` 約等於 Python 的 `import`。
2. C++ 的 class/struct 還在，但 Python 用縮排決定區塊，不用大括號。
3. C++ 的 `std::string` 在 Python 是 `str`。
4. C++ 的 `std::vector` 在 Python 常用 `list`。
5. C++ 的 `std::map` 在 Python 常用 `dict`。
6. C++ 需要型別宣告；Python 多數時候不強制，但本專案部分函式有 type hints。

## 本專案你只要先懂的執行鏈

1. `app.py` 產生 challenge，並等待 response。
2. `mqtt_bridge.py` 把 challenge 發到 MQTT，並把裝置回覆寫回本地檔案。
3. `node.py` 收到 challenge，呼叫 `simulate_puf_response` 回傳 response。
4. `app.py` 計算 Hamming Distance，依 threshold 判定通過/失敗。

## 你最常改到的地方

1. `app.py`：
- 調整認證流程、UI 按鈕、門檻值。
- 看 `calculate_hamming_distance` 與 challenge 發送區塊。

2. `puf_simulator.py`：
- 調噪聲模型（`noise_sigma`、bias/unsteady bits）。
- 用於批次實驗和理論分析。

3. `batch_test.py`：
- 調整測試次數、輸出檔名、threshold 掃描範圍。

## Python 語法最小包（你會遇到的）

### 1) 函式

```python
def add(a, b):
    return a + b
```

### 2) 字典（像 C++ 的 map）

```python
payload = {
    "challenge": challenge,
    "noise_level": 3,
}
```

### 3) 例外處理（像 try/catch）

```python
try:
    do_something()
except Exception as e:
    print(e)
```

### 4) 讀寫 JSON 檔（本專案常見）

```python
import json

with open("response_in.json", "r", encoding="utf-8") as f:
    data = json.load(f)
```

## 你可以用這個方式理解程式

1. 先找 `if __name__ == "__main__":`（主程式入口）。
2. 再看 `main()` 裡的流程呼叫順序。
3. 最後才進去看每個函式細節。

## 常見除錯方法

1. 先看 terminal 的錯誤堆疊（Traceback 最下面那行最關鍵）。
2. 檢查 JSON 格式是否正確（尤其 `challenge_out.json`、`response_in.json`）。
3. 確認三個程序都在跑：`app.py`, `mqtt_bridge.py`, `node.py`。
4. 如果 UI 沒收到回應，先看 `mqtt_bridge.py` 日誌是否有收到 `response` topic。

## 一鍵啟動順序（手動）

```bash
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
python -m streamlit run app.py
python mqtt_bridge.py
python node.py
```

## 你現在可以先做的第一個小改動

把 `batch_test.py` 的測試次數改成 30/30，確認你可以成功跑完並在 `artifacts/` 看到輸出。

這是最安全、最容易建立信心的入口。
