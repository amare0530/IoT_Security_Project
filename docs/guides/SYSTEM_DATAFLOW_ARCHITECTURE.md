# 系統資料流架構圖

```mermaid
flowchart LR
    A[Server: Streamlit app.py\n動態 Challenge + Nonce] -->|challenge, nonce, timestamp| B[mqtt_bridge.py]
    B -->|MQTT publish| C[Node / PUF Endpoint]
    C -->|response + noise + metadata| B
    B -->|IPC file response_in.json| A

    A --> S
    subgraph S[Security Engine]
        D[Nonce 防重放檢查]
        D2[Timestamp 驗證]
        D3[Hamming Distance 判定]
    end
    S --> E[(SQLite auth_history)]
    E --> F[歷史頁 UI\n依 source 篩選 real/simulated]

    G[開源或實測資料 CSV] --> H[real_data_ingest.py\n驗證與正規化]
    H --> I[(SQLite crp_records)]
    I --> J[Benchmark / 分析腳本]

    S --> J
```

## 簡述
1. 即時驗證路徑：Server 發 challenge，Node 回 response，Security Engine 執行 nonce、timestamp、HD 驗證後寫入資料庫。
2. 資料集路徑：開源/實測 CSV 先經 `real_data_ingest.py` 檢查，再寫入 `crp_records`。
3. 分析路徑：分析腳本可同時吃即時驗證資料與匯入資料做 FAR/FRR/EER 對照。




