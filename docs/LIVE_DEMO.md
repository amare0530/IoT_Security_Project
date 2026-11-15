# 口試現場展示（VS Code 三個終端機）

三個面板都在 VS Code 的終端機裡跑，看到的是真的程式、真的封包。

| 面板 | 指令 | 角色 |
|---|---|---|
| Server | `py -3.11 -m demo.server` | 讀金鑰登錄表、發 challenge、六關檢查 |
| Device | `py -3.11 -m demo.device` | 讀 helper data 與 SRAM 開機值、重建金鑰、回應 |
| Hacker | `py -3.11 -m demo.hacker` | 沒有金鑰，只能側錄與發送封包，給評審操作 |

`demo/` 只負責畫面與操作。通過或拒絕由原本的函式決定：
`mqtt/server.py` 的 `classify_response`、`auth/hmac_auth.py` 的
`PUFAuthenticator`、`puf/fuzzy_extractor.py` 的 `rep`。原本的
`mqtt/server.py`、`mqtt/device.py` 沒有改動。

## 啟動

1. 確認 Mosquitto 已在跑（1883 port）。沒有的話：`mosquitto -c mosquitto-demo.conf -v`
2. 確認專案根目錄有 `demo_bundle/`（由 `scripts/export_demo_bundle.py` 從真實資料集匯出）
3. VS Code：`Ctrl+Shift+P` → `Tasks: Run Task` → `demo: 全部啟動`，三個面板會並排開啟

沒有帶 UID 參數時，Server 與 Device 會自動使用 bundle 裡唯一的那個 UID。

第二台筆電當駭客機時，在那台執行（IP 換成主機的區網 IP）：

```powershell
py -3.11 -m demo.hacker --broker 192.168.x.x
```

「換晶片」需要另一台設備的開機值，匯出 bundle 時多加一個參數：

```powershell
py -3.11 scripts/export_demo_bundle.py --uid <展示用 UID> --crps data/crps.csv --attacker-uid <另一台的 UID>
```

匯出時會印出 `wrong-chip check: ... matches registered=no`，確認別顆晶片重建不出同一把金鑰。

## 操作

| 面板 | 輸入 | 發生的事 |
|---|---|---|
| Device | Enter | 開機認證：金鑰投票重建、送出回應、Server 六關全過 |
| Device | `n 5` | 人工翻轉 5% 位元後認證，多數決救回，仍通過 |
| Device | `n 30` | 雜訊超過容錯範圍，重建出錯的金鑰，被拒絕 |
| Device | `x` | 換成別顆晶片的 SRAM（helper data 不變），被拒絕 |
| Hacker | `1` | 重放剛才側錄到的封包，停在第 3 關 |
| Hacker | `2` | 自己改封包任一欄位再送：改 uid 停第 2 關、改 nonce 或 timestamp 停第 4 關、改 hmac 停第 6 關 |
| Hacker | `3` | 對同一個 challenge 連續亂猜 1,000 次，全部停在第 6 關 |
| Hacker | `4` | 破解對照組的 4 位數密碼（無防護版本），幾秒內成功 |
| Hacker | 任意文字 | 把那串字當成密碼送出 |

Server 面板拒絕時會印出 `程式位置 mqtt/server.py:行號`，在 VS Code 終端機
按住 Ctrl 點一下就會跳到那一行判斷式。

## 建議流程（約 4 分鐘）

1. Hacker `4`：對照組被破解，說明只靠密碼的設備會怎樣
2. Device Enter：正常認證，指出 Device 與 Server 兩邊的金鑰指紋相同
3. 指著 Hacker 面板側錄到的封包：只有四個欄位，沒有金鑰
4. 請評審在 Hacker 面板操作 `1`、`2`、任意文字、`3`
5. Device `x` 或 `n 30`，再按一次 Enter 證明正常設備仍然通過

## 現場要如實說明的事

- SRAM 開機值來自公開資料集，不是現場從晶片量測
- `n` 的雜訊是人工翻轉，和報告中的 5% BER 實驗做法相同
- 金鑰指紋是展示用的雜湊前 8 碼，方便肉眼比對；金鑰本身不顯示、不上網
- 對照組的 4 位數密碼登入是為了對比而寫的，不是本系統的一部分
- 攻擊者是 MQTT 訂閱者，只能側錄與發送，不能攔下封包；封包沒有加密，保密需另加 TLS
- 計分是「本次展示的攻擊」結果，不是系統無法被攻破的證明
- `iot/auth/demo/control` 是展示用的觸發 topic（請 Server 發 challenge），正式協定沒有這個 topic

## 沒有資料集的電腦要排練

```powershell
py -3.11 -m demo.make_synthetic_bundle --out demo_bundle
```

這份是亂數產生的，不是 SRAM 量測，只能排練用。
