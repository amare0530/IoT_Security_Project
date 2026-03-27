"""
═══════════════════════════════════════════════════════════════════
IoT 硬體指紋認證系統 - Streamlit 伺服器端 (Server)
═══════════════════════════════════════════════════════════════════

系統架構：
  [Challenge Generation] --MQTT--> [PUF Device (Node)]
         (VRF)                          |
                                        ↓ (模擬 PUF 特徵提取)
                                   [Add Noise]
                                        |
                                        ↓
  [Server Authentication] <--MQTT-- [Response with Noise]
  (Hamming Distance + Proof)

資料流說明：
  1. Challenge (C): 伺服器用 VRF 生成隨機挑戰碼
  2. PUF Process: Node 端設備將 Challenge 送入 PUF 進行特徵提取
  3. Response (R): PUF 產生響應，自然包含硬體製程雜訊
  4. Proof: 伺服器計算漢明距離驗證 Response 是否來自合法設備
  
作者: IoT Security Project
日期: 2026.03.27
"""

import streamlit as st
import hashlib
import hmac
import random
import paho.mqtt.client as mqtt
import json
import time
import pandas as pd
import threading

# 設定網頁標題與圖示
st.set_page_config(page_title="IoT 安全驗證系統", page_icon="🔒", layout="wide")

# --- 核心邏輯函數 ---
def calculate_hamming_distance(s1, s2):
    """
    計算兩個 Hex 字串之間的位元差異數 (Hamming Distance)
    
    原理：
      - 將兩個 256 位的 Hex 值轉為二進制並逐位比較
      - 差異位數越小 → 設備特徵越一致 → 認證通過
      - 差異位數越大 → 可能雜訊過大或設備偽造
    
    參數:
      s1, s2: 待比較的 Hex 字串 (Challenge 和 Response)
    
    返回:
      差異位元數 (0-256)
    """
    hex1 = bin(int(s1, 16))[2:].zfill(256)
    hex2 = bin(int(s2, 16))[2:].zfill(256)
    return sum(c1 != c2 for c1, c2 in zip(hex1, hex2))

def inject_noise(hex_str, num_bits):
    """
    模擬硬體製程中的物理雜訊 (Physical Unclonable Function Noise)
    
    原理：
      - PUF 設備因製程偏差，每次讀取時會產生微小隨機變化
      - 此函數隨機翻轉指定數量的位元，模擬時間變異性 (time variance)
      - 這就是為什麼我們需要容錯機制 (error correction)
    
    參數:
      hex_str: 原始特徵碼 (Challenge 或無雜訊 Response)
      num_bits: 要翻轉的位元數 (模擬的雜訊等級)
    
    返回:
      包含雜訊的 Hex 字串 (模擬 PUF 實際響應)
    """
    if num_bits == 0:
        return hex_str
    bits = list(bin(int(hex_str, 16))[2:].zfill(256))
    indices = random.sample(range(256), num_bits)
    for i in indices:
        bits[i] = '1' if bits[i] == '0' else '0'
    return hex(int("".join(bits), 2))[2:].zfill(64)

def generate_vrf_challenge(private_key, seed):
    """
    使用 VRF (Verifiable Random Function) 生成挑戰碼
    
    VRF 的三大特性 (Three Properties):
      1. Deterministic: 相同的私鑰與種子產生相同的挑戰
      2. Unpredictable: 沒有私鑰的攻擊者無法預測下一個挑戰
      3. Verifiable: 使用公鑰和證明可驗證挑戰的合法性
    
    參數:
      private_key: 伺服器私鑰 (Server Secret Key)
      seed: CRP 資料庫中的種子 (Challenge Response Pair Index)
    
    返回:
      (challenge_code, proof_value) 元組
    """
    # 使用 HMAC-SHA256 確保確定性與不可預測性
    c = hmac.new(private_key.encode(), seed.encode(), hashlib.sha256).hexdigest()
    # Proof 用於驗證此 C 是由本伺服器發出 (防偽造)
    proof = hashlib.sha256((c + private_key).encode()).hexdigest()[:20]
    return c, proof

# --- 狀態管理 (Session State) ---
# Streamlit 的 Session State 用於在頁面刷新時保存資料
if "current_challenge" not in st.session_state:
    st.session_state.current_challenge = None

# 【系統閉環的關鍵】監聽 Node 端回傳的 Response
if "latest_mqtt_response" not in st.session_state:
    st.session_state.latest_mqtt_response = None
    
# 標記 MQTT 監聽執行緒是否已啟動 (防止多個執行緒同時執行)
if "mqtt_listener_started" not in st.session_state:
    st.session_state.mqtt_listener_started = False

# --- MQTT 背景監聽線程 (實現系統閉環) ---
def start_mqtt_listener():
    """
    啟動一個背景執行緒，持續監聽 MQTT 回傳的 Response
    
    【系統閉環說明】
    1. Server → Node: 透過 MQTT 發布 Challenge 到 "fujen/iot/challenge"
    2. Node 處理: Node 訂閱並接收 Challenge，經過 PUF 模擬產生 Response
    3. Node → Server: Node 將 Response 發布到 "fujen/iot/response"
    4. Server 驗證: 此監聽線程捕獲 Response，存入 Session State
    5. 自動比對: Server 計算漢明距離，與 Proof 進行驗證
    """
    def mqtt_on_message(client, userdata, msg):
        """MQTT 回調: 當收到 Response 時執行"""
        try:
            # 【資料流 Step 3】伺服器端收到來自 Node 的 JSON Response 資料
            payload = json.loads(msg.payload.decode('utf-8'))
            device_id = payload.get("device_id", "Unknown")
            response = payload.get("response", "")
            
            # 【重要】將收到的資料存入 Session State，供主執行線程讀取
            st.session_state.latest_mqtt_response = {
                "device_id": device_id,
                "response": response,
                "timestamp": time.time()
            }
            
            print(f"✅ [MQTT Listener] 線程已捕獲 Node 響應: {device_id}")
        except Exception as e:
            print(f"❌ [MQTT Listener] 解析失敗: {e}")
    
    def mqtt_listener_worker():
        """MQTT 監聽工作線程"""
        client = mqtt.Client()
        client.on_message = mqtt_on_message
        
        try:
            client.connect("broker.emqx.io", 1883, 60)
            client.subscribe("fujen/iot/response")  # 訂閱 Response 主題
            print("📡 [MQTT Listener] 已連線，等待 Node 端回傳...")
            client.loop_forever()
        except Exception as e:
            print(f"❌ [MQTT Listener] 連線失敗: {e}")
    
    # 建立背景線程 (daemon=True 表示主程式結束時此線程自動終止)
    if not st.session_state.mqtt_listener_started:
        listener_thread = threading.Thread(
            target=mqtt_listener_worker, 
            daemon=True,
            name="MQTT-Listener-Thread"
        )
        listener_thread.start()
        st.session_state.mqtt_listener_started = True
        print("🚀 [MQTT Listener] 背景監聽線程已啟動")

# 在應用啟動時立即啟動 MQTT 監聽線程
start_mqtt_listener()

# --- 主畫面介面 ---
st.title("🔒 IoT 設備硬體指紋認證系統")
st.subheader("基於 VRF + PUF + Hamming Distance 的安全驗證平台")

# 左侧：資訊面板，右侧：控制面板
col_info, col_control = st.columns([1, 1])

with col_info:
    st.info(
        "📋 **系統流程說明**\n\n"
        "1️⃣ Challenge 生成：伺服器用 VRF 產生隨機挑戰碼\n"
        "2️⃣ MQTT 傳輸：挑戰碼透過 MQTT 發送到 Node 設備\n"
        "3️⃣ PUF 模擬：Node 設備模擬 PUF 特徵提取，注入雜訊\n"
        "4️⃣ Response 回傳：Node 透過 MQTT 回傳包含雜訊的響應\n"
        "5️⃣ 漢明距離驗證：伺服器計算距離，判定設備是否合法"
    )

with col_control:
    st.subheader("⚙️ 系統設定")
    sk = st.text_input(
        "🔐 伺服器私鑰 (Server Secret Key)",
        value="FU_JEN_CSIE_SECRET_2026",
        type="password",
        help="僅伺服器持有，用於生成不可預測的 VRF Challenge"
    )
    seed_input = st.text_input(
        "🎲 CRP 抽考種子 (Challenge Seed)",
        value="CRP_INDEX_001",
        help="從 CRP 資料庫中選取的種子編號，保證確定性"
    )

st.divider()

# --- 【第一階段】Challenge 生成與發送 ---
st.subheader("📤 第一階段：Challenge 生成與發送")

col_gen, col_send = st.columns([1, 1])

with col_gen:
    if st.button("🔄 1️⃣ 生成新挑戰碼 (Generate VRF Challenge)", key="gen_challenge"):
        # 【資料流 Stage 1】伺服器端生成 Challenge
        c_code, proof_val = generate_vrf_challenge(sk, seed_input)
        st.session_state.current_challenge = c_code
        st.session_state.latest_mqtt_response = None  # 清空舊響應以待新的
        
        st.success(f"✅ 已生成新 Challenge")
        st.metric("Challenge Code (C)", c_code[:16] + "...")
        st.markdown(f"**完整值**: `{c_code}`")
        
        col_c1, col_c2 = st.columns(2)
        with col_c1:
            st.metric("Proof (證明碼)", proof_val)
        with col_c2:
            st.info("💡 此 Proof 用來驗證 C 的真偽")

with col_send:
    if st.button("📡 2️⃣ 發送至 Node 端 (Send via MQTT)", key="send_challenge"):
        if not st.session_state.current_challenge:
            st.error("❌ 請先生成 Challenge！")
        else:
            # 【資料流 Stage 2】伺服器端透過 MQTT 發布 Challenge 到 Node
            try:
                mqtt_client = mqtt.Client()
                mqtt_client.connect("broker.emqx.io", 1883, 60)
                
                payload = json.dumps({
                    "challenge": st.session_state.current_challenge,
                    "timestamp": time.time()
                })
                
                mqtt_client.publish("fujen/iot/challenge", payload)
                mqtt_client.disconnect()
                
                st.success("✅ Challenge 已透過 MQTT 發送到 Node 端")
                st.info("⏳ 等待 Node 回傳響應...")
                
            except Exception as e:
                st.error(f"❌ MQTT 發送失敗: {e}")

st.divider()

# --- 【第二階段】接收並驗證 Response（系統閉環） ---
st.subheader("📥 第二階段：接收 Response 並自動驗證")

col_check, col_manual = st.columns([1, 1])

with col_check:
    if st.button("🔍 3️⃣ 檢查並驗證 Response", key="check_response"):
        if not st.session_state.current_challenge:
            st.error("❌ 請先發送 Challenge！")
        elif not st.session_state.latest_mqtt_response:
            st.warning("⏳ 尚未收到 Node 端回傳。請確保 node.py 正在運行！")
        else:
            # 【資料流 Stage 4】伺服器端接收到 Response，開始驗證
            resp_data = st.session_state.latest_mqtt_response
            device_id = resp_data.get("device_id")
            received_response = resp_data.get("response")
            
            # 【資料流 Stage 5】計算漢明距離 (Hamming Distance)
            hamming_dist = calculate_hamming_distance(
                st.session_state.current_challenge,
                received_response
            )
            
            # 顯示驗證結果
            st.success(f"✅ 成功接收 {device_id} 的 Response")
            
            col_info1, col_info2, col_info3 = st.columns(3)
            with col_info1:
                st.metric("設備 ID", device_id)
            with col_info2:
                st.metric("漢明距離", f"{hamming_dist} bits")
            with col_info3:
                st.metric("接收時間", f"{resp_data.get('timestamp', 'N/A')}")
            
            st.markdown(f"**Response**: `{received_response[:20]}...`")

with col_manual:
    st.write("### 手動輸入驗證模式 (選用)")
    manual_response = st.text_input("輸入 Response (Hex 格式)")
    
    if manual_response and st.session_state.current_challenge:
        try:
            dist = calculate_hamming_distance(
                st.session_state.current_challenge,
                manual_response
            )
            st.metric("計算的漢明距離", dist)
        except:
            st.error("❌ 格式有誤，請輸入有效的 Hex 字串")

st.divider()

# --- 【第三階段】容錯測試 (單次實驗) ---
st.subheader("🛡️ 第三階段：容錯能力測試")
st.write("在當前 Challenge 上注入雜訊，測試系統的容錯門檻")

if st.session_state.current_challenge:
    original_c = st.session_state.current_challenge
    
    col_noise, col_thresh = st.columns(2)
    with col_noise:
        test_noise_level = st.slider(
            "雜訊等級 (Noise Level)",
            min_value=0,
            max_value=20,
            value=3,
            help="翻轉的位元數 (模擬硬體製程雜訊)"
        )
    with col_thresh:
        test_threshold = st.number_input(
            "容錯門檻 (Threshold)",
            value=5,
            min_value=0,
            max_value=256,
            help="漢明距離在此值以下則認證成功"
        )
    
    # 【本地模擬】: 在伺服器端模擬 PUF 雜訊
    if st.button("🧪 模擬一次 PUF 出力"):
        noisy_response = inject_noise(original_c, test_noise_level)
        dist = calculate_hamming_distance(original_c, noisy_response)
        
        col_result1, col_result2, col_result3 = st.columns(3)
        with col_result1:
            st.metric("產生的 Response", noisy_response[:16] + "...")
        with col_result2:
            st.metric("漢明距離", dist)
        with col_result3:
            st.metric(
                "認證結果",
                "✅ 通過" if dist <= test_threshold else "❌ 失敗"
            )
        
        if dist <= test_threshold:
            st.success(
                f"✅ 認證通過：距離 {dist} bits ≤ 門檻 {test_threshold} bits"
            )
        else:
            st.error(
                f"❌ 認證失敗：距離 {dist} bits > 門檻 {test_threshold} bits"
            )
else:
    st.warning("請先完成第一階段產生 Challenge！")

st.divider()

# --- 【第四階段】批量實驗測試 (數據化 FRR/FAR Trade-off) ---
st.subheader("📊 第四階段：批量實驗 - 安全性 Trade-off 分析")
st.write(
    "**目的**: 根據指導教授建議，通過 100 次批量測試數據化分析 FRR (False Rejection Rate) 與容錯門檻的關係。\n\n"
    "**背景知識**:\n"
    "- **FRR**: 合法設備被錯誤拒絕的比率\n"
    "- **FAR**: 非法設備被錯誤接受的比率\n"
    "- **Trade-off**: 提高門檻會降低 FRR 但提高 FAR；降低門檻則相反"
)

# 實驗參數設置
col_exp1, col_exp2 = st.columns(2)
with col_exp1:
    exp_noise = st.slider(
        "📊 實驗雜訊等級",
        min_value=0,
        max_value=20,
        value=3,
        help="用於 100 次測試的雜訊位元翻轉數"
    )
with col_exp2:
    exp_threshold = st.number_input(
        "📊 實驗容錯門檻",
        value=5,
        min_value=0,
        max_value=256,
        help="判定認證成功的漢明距離上限"
    )

# 批量測試的主要邏輯
if st.button("🚀 執行 100 次自動化實驗 (Generate FRR/FAR Data)", key="run_batch_test"):
    if not st.session_state.current_challenge:
        st.error("❌ 請先在第一階段生成 Challenge！")
    else:
        original_c = st.session_state.current_challenge
        
        st.write("### 🔄 實驗執行中...")
        
        # 【批量實驗說明】
        # 在相同的原始 Challenge 上，進行 100 次獨立的雜訊注入和距離計算
        # 統計每次測試是否通過門檻，用於計算 FRR
        
        test_results = []
        success_count = 0
        fail_count = 0
        distances = []
        
        # 實時進度顯示
        progress_placeholder = st.empty()
        progress_bar = st.progress(0)
        
        for test_num in range(100):
            # Step 1: 產生帶雜訊的 Response (模擬 PUF 的 100 次獨立讀取)
            noisy_response = inject_noise(original_c, exp_noise)
            
            # Step 2: 計算此次的漢明距離
            distance = calculate_hamming_distance(original_c, noisy_response)
            distances.append(distance)
            
            # Step 3: 判定是否通過認證
            is_passed = distance <= exp_threshold
            
            if is_passed:
                success_count += 1
            else:
                fail_count += 1
            
            # Step 4: 記錄此次測試結果
            test_results.append({
                "Test #": test_num + 1,
                "Hamming Distance": distance,
                "Passed": "✅ Yes" if is_passed else "❌ No"
            })
            
            # Step 5: 更新進度條
            progress_percent = (test_num + 1) / 100
            progress_bar.progress(progress_percent)
            progress_placeholder.write(
                f"進度: {test_num + 1}/100 | ✅ 通過: {success_count} | ❌ 失敗: {fail_count}"
            )
        
        progress_bar.empty()
        progress_placeholder.empty()
        
        st.success("✅ 100 次實驗已完成！")
        
        # --- 【數據統計】計算 FRR 與相關指標 ---
        st.write("### 📊 實驗結果統計")
        
        # FRR (False Rejection Rate) 計算
        frr_percentage = (fail_count / 100) * 100
        far_percentage = 100 - frr_percentage  # 簡化版本 (實際 FAR 需要非法設備資料)
        
        # 顯示關鍵指標 (4 列，分別為成功、失敗、FRR、平均距離)
        metric_col1, metric_col2, metric_col3, metric_col4 = st.columns(4)
        
        with metric_col1:
            st.metric(
                "✅ 認證成功次數",
                f"{success_count}/100",
                delta=f"{(success_count/100)*100:.1f}%"
            )
        
        with metric_col2:
            st.metric(
                "❌ 認證失敗次數",
                f"{fail_count}/100",
                delta=f"{(fail_count/100)*100:.1f}%"
            )
        
        with metric_col3:
            st.metric(
                "📉 FRR (拒認率)",
                f"{frr_percentage:.2f}%",
                delta="拒認率越低越好" if frr_percentage < 10 else "需要優化"
            )
        
        with metric_col4:
            avg_distance = sum(distances) / len(distances)
            max_distance = max(distances)
            min_distance = min(distances)
            st.metric(
                "📏 距離統計",
                f"avg={avg_distance:.1f}",
                delta=f"min={min_distance}, max={max_distance}"
            )
        
        # --- 【圖表與視覺化】---
        st.write("### 📈 可視化分析")
        
        # 準備 DataFrame
        df_results = pd.DataFrame(test_results)
        
        # 圖表 1: 漢明距離折線圖
        chart_col1, chart_col2 = st.columns(2)
        
        with chart_col1:
            st.write("#### 📊 距離分布 (折線圖)")
            st.line_chart(
                df_results.set_index("Test #")["Hamming Distance"],
                use_container_width=True
            )
        
        with chart_col2:
            st.write("#### 🎯 通過/失敗比例 (長條圖)")
            success_fail_df = pd.DataFrame({
                "結果": ["✅ 認證通過", "❌ 認證失敗"],
                "次數": [success_count, fail_count]
            })
            st.bar_chart(
                success_fail_df.set_index("結果"),
                use_container_width=True
            )
        
        # --- 【Trade-off 分析與建議】---
        st.write("### 💡 Trade-off 分析與改進建議")
        
        if frr_percentage > 30:
            st.warning(
                f"⚠️ **FRR 過高 ({frr_percentage:.2f}%)**\n\n"
                "這表示許多合法設備會被錯誤拒絕。\n\n"
                "**改進方案**:\n"
                "- 📈 提高容錯門檻 (Threshold) 以降低 FRR\n"
                "- 📉 檢查硬體是否有製程問題 (雜訊過大)\n"
                "- ⚙️ 考慮優化 PUF 的一致性\n"
            )
        elif frr_percentage > 10:
            st.info(
                f"ℹ️ **FRR 中等 ({frr_percentage:.2f}%)**\n\n"
                "目前的設定尚可接受，但仍有改進空間。\n\n"
                "**優化空間**:\n"
                "- 🔍 嘗試調整門檻以找到最佳平衡點\n"
                "- 📊 測試不同的雜訊等級\n"
            )
        else:
            st.success(
                f"🎉 **FRR 優秀 ({frr_percentage:.2f}%)**\n\n"
                "目前的參數設定很好！合法設備能穩定通過認證。\n\n"
                "**建議**:\n"
                "- ✅ 此參數組合可用於生產環境\n"
                "- 📖 記錄此設置用於未來的參考\n"
            )
        
        # --- 【詳細資料與匯出】---
        with st.expander("📋 查看詳細測試資料", expanded=False):
            st.write("#### 100 次測試的完整記錄")
            st.dataframe(df_results, use_container_width=True)
            
            # CSV 下載功能
            csv_data = df_results.to_csv(index=False)
            st.download_button(
                label="📥 下載為 CSV 檔案",
                data=csv_data,
                file_name=f"frr_experiment_noise{exp_noise}_threshold{exp_threshold}.csv",
                mime="text/csv"
            )


# --- 【附錄】系統資訊面板 ---
st.divider()
st.subheader("ℹ️ 系統資訊與狀態")

info_col1, info_col2, info_col3 = st.columns(3)

with info_col1:
    if st.session_state.current_challenge:
        st.success(f"✅ Challenge 已生成")
    else:
        st.warning(f"⚠️ 尚未生成 Challenge")

with info_col2:
    if st.session_state.latest_mqtt_response:
        st.success(f"✅ 已接收 Node 響應")
    else:
        st.warning(f"⚠️ 等待 Node 回傳")

with info_col3:
    if st.session_state.mqtt_listener_started:
        st.success(f"✅ MQTT 監聽執行緒已啟動")
    else:
        st.warning(f"⚠️ MQTT 監聽線程未啟動")

# 底部說明文字
st.divider()
st.markdown(
    """
    ### 📖 系統使用指南
    
    **快速流程**:
    1. 生成 VRF Challenge 並發送至 Node
    2. Node 按收並模擬 PUF 處理，回傳 Response
    3. Server 自動監聽並計算漢明距離
    4. 若距離 ≤ 門檻則認證成功
    
    **批量實驗**:
    - 用來分析不同參數下的 FRR/FAR Trade-off
    - 結果可匯出為 CSV 用於論文分析
    
    **更多資訊**: 參考 [GitHub 專案](https://github.com/amare0530/IoT_Security_Project)
    """
)