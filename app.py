"""
═══════════════════════════════════════════════════════════════════
IoT 硬體指紋認證系統 - Streamlit 伺服器端 (Server)
增強版本 - 集成 SQLite 數據庫 & 完善異常處理
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

主要改進：
  ✅ SQLite 數據庫持久化存儲
  ✅ 完善的異常處理與錯誤提示
  ✅ MQTT 線程安全性優化
  ✅ 歷史記錄查詢與分析
  ✅ 批量實驗結果統計
  
作者: IoT Security Project
日期: 2026.03.29 (Enhanced)
"""

import streamlit as st
import hashlib
import hmac
import random
import json
import time
import pandas as pd
import sqlite3
from datetime import datetime
import os
import traceback

# ═══════════════════════════════════════════════════════════════
# 【頁面配置】
# ═══════════════════════════════════════════════════════════════

st.set_page_config(
    page_title="IoT 安全驗證系統",
    page_icon="🔒",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ═══════════════════════════════════════════════════════════════
# 【數據庫管理模組】
# ═══════════════════════════════════════════════════════════════

DB_PATH = "authentication_history.db"

def init_database():
    """初始化 SQLite 數據庫與認證歷史表"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # 認證歷史表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS auth_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                device_id TEXT NOT NULL,
                challenge TEXT NOT NULL,
                response TEXT NOT NULL,
                hamming_distance INTEGER NOT NULL,
                threshold INTEGER NOT NULL,
                result TEXT NOT NULL,
                noise_level INTEGER,
                is_batch INTEGER DEFAULT 0,
                batch_id TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 批量實驗統計表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS batch_experiments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                batch_id TEXT UNIQUE NOT NULL,
                timestamp TEXT NOT NULL,
                noise_level INTEGER,
                threshold INTEGER,
                total_tests INTEGER,
                passed_tests INTEGER,
                failed_tests INTEGER,
                frr REAL,
                avg_distance REAL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 索引優化
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_timestamp ON auth_history(timestamp)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_device ON auth_history(device_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_batch ON auth_history(batch_id)')
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        st.error(f"❌ 資料庫初始化失敗: {str(e)}")
        return False

def save_auth_result(device_id, challenge, response, hamming_distance, threshold, result, noise_level=None, batch_id=None):
    """將認證結果儲存至資料庫"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        is_batch = 1 if batch_id else 0
        
        cursor.execute('''
            INSERT INTO auth_history 
            (timestamp, device_id, challenge, response, hamming_distance, threshold, result, noise_level, is_batch, batch_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (timestamp, device_id, challenge, response, hamming_distance, threshold, result, noise_level, is_batch, batch_id))
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        st.warning(f"⚠️ 保存認證記錄失敗: {str(e)}")
        return False

def save_batch_experiment(batch_id, noise_level, threshold, total, passed, failed, frr, avg_distance):
    """保存批量實驗統計"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        cursor.execute('''
            INSERT INTO batch_experiments 
            (batch_id, timestamp, noise_level, threshold, total_tests, passed_tests, failed_tests, frr, avg_distance)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (batch_id, timestamp, noise_level, threshold, total, passed, failed, frr, avg_distance))
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        st.warning(f"⚠️ 保存批量實驗結果失敗: {str(e)}")
        return False

def get_auth_history(limit=100, device_id=None, is_batch=None):
    """查詢認證歷史記錄"""
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        
        query = "SELECT * FROM auth_history WHERE 1=1"
        params = []
        
        if device_id:
            query += " AND device_id = ?"
            params.append(device_id)
        
        if is_batch is not None:
            query += " AND is_batch = ?"
            params.append(is_batch)
        
        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)
        
        df = pd.read_sql_query(query, conn, params=params)
        conn.close()
        
        return df
    except Exception as e:
        st.error(f"❌ 查詢歷史記錄失敗: {str(e)}")
        return pd.DataFrame()

def get_batch_statistics(batch_id):
    """取得批量實驗統計"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM batch_experiments WHERE batch_id = ?
        ''', (batch_id,))
        
        result = cursor.fetchone()
        conn.close()
        
        return result
    except Exception as e:
        st.error(f"❌ 查詢統計失敗: {str(e)}")
        return None

def get_all_batch_experiments(limit=20):
    """取得所有批量實驗記錄"""
    try:
        conn = sqlite3.connect(DB_PATH)
        df = pd.read_sql_query(
            "SELECT * FROM batch_experiments ORDER BY timestamp DESC LIMIT ?",
            conn,
            params=(limit,)
        )
        conn.close()
        return df
    except Exception as e:
        st.error(f"❌ 查詢批量實驗失敗: {str(e)}")
        return pd.DataFrame()

def export_history_to_csv():
    """匯出認證歷史為 CSV"""
    try:
        df = get_auth_history(limit=10000)
        if df.empty:
            return None
        return df.to_csv(index=False)
    except Exception as e:
        st.error(f"❌ 匯出失敗: {str(e)}")
        return None

# 程式啟動時初始化資料庫
init_database()

# ═══════════════════════════════════════════════════════════════
# 【核心邏輯函數】
# ═══════════════════════════════════════════════════════════════

def calculate_hamming_distance(s1, s2):
    """
    計算兩個 Hex 字串之間的漢明距離
    """
    try:
        # 驗證輸入
        if not s1 or not s2:
            raise ValueError("Challenge 或 Response 不能為空")
        
        # 轉為二進制
        hex1 = bin(int(s1, 16))[2:].zfill(256)
        hex2 = bin(int(s2, 16))[2:].zfill(256)
        
        # 計算不同位元數
        distance = sum(c1 != c2 for c1, c2 in zip(hex1, hex2))
        return distance
    except ValueError as e:
        st.error(f"❌ Hex 格式錯誤: {str(e)}")
        return None
    except Exception as e:
        st.error(f"❌ 計算漢明距離時發生錯誤: {str(e)}")
        return None

def inject_noise(hex_str, num_bits):
    """模擬硬體製程雜訊"""
    try:
        if num_bits == 0:
            return hex_str
        
        if num_bits > 256:
            raise ValueError("雜訊位元數不能超過 256")
        
        bits = list(bin(int(hex_str, 16))[2:].zfill(256))
        indices = random.sample(range(256), num_bits)
        
        for i in indices:
            bits[i] = '1' if bits[i] == '0' else '0'
        
        return hex(int("".join(bits), 2))[2:].zfill(64)
    except Exception as e:
        st.error(f"❌ 注入雜訊時發生錯誤: {str(e)}")
        return None

def generate_vrf_challenge(private_key, seed):
    """使用 VRF 生成挑戰碼"""
    try:
        if not private_key or not seed:
            raise ValueError("私鑰和種子不能為空")
        
        # HMAC-SHA256 產生確定性挑戰
        c = hmac.new(private_key.encode(), seed.encode(), hashlib.sha256).hexdigest()
        
        # 生成 Proof
        proof = hashlib.sha256((c + private_key).encode()).hexdigest()[:20]
        
        return c, proof
    except Exception as e:
        st.error(f"❌ VRF 生成失敗: {str(e)}")
        return None, None

# ═══════════════════════════════════════════════════════════════
# 【Session 狀態管理】
# ═══════════════════════════════════════════════════════════════

if "current_challenge" not in st.session_state:
    st.session_state.current_challenge = None

if "bridge_status" not in st.session_state:
    st.session_state.bridge_status = "未知🚀"

# ==========================================
# File-based IPC (與 mqtt_bridge.py 通信)
# ==========================================

import os, json, time

OUT_FILE = "response_in.json"
IN_FILE = "challenge_out.json"

def get_latest_response():
    try:
        if os.path.exists(OUT_FILE):
            with open(OUT_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                resp = data.get("response")
                recv_time = data.get("received_time")
                if resp and recv_time:
                    return resp, recv_time
    except Exception:
        pass
    return None, None

def clear_response():
    try:
        with open(OUT_FILE, "w", encoding="utf-8") as f:
            json.dump({}, f)
    except:
        pass

def send_challenge_to_bridge(challenge, noise_level=3):
    try:
        with open(IN_FILE, "w", encoding="utf-8") as f:
            json.dump({
                "challenge": challenge,
                "noise_level": noise_level,
                "timestamp": time.time()
            }, f, indent=2)
        return True
    except Exception as e:
        import streamlit as st
        st.error(f"發送 Challenge 失敗: {e}")
        return False


st.title("🔒 IoT 設備硬體指紋認證系統")
st.subheader("基於 VRF + PUF + Hamming Distance 的安全驗證平台")

# ═══════════════════════════════════════════════════════════════
# 【MQTT 實時診斷面板】
# ═══════════════════════════════════════════════════════════════

with st.expander("Bridge 連線狀態與測試", expanded=True):
    col_d1, col_d2, col_d3 = st.columns(3)

    with col_d1:
        st.markdown("**Bridge 狀態**")
        st.success("✅ IPC 模式已啟用")

    with col_d2:
        st.markdown("**最後 Response**")
        latest_resp, last_time = get_latest_response()
        if latest_resp is not None and last_time is not None:
            time_ago = time.time() - last_time
            st.success(f"約 {time_ago:.1f} 秒前")
        else:
            st.warning("尚未收到")

    with col_d3:
        st.markdown("**手動操作**")
        if st.button("刷新 UI", key="refresh_ui", use_container_width=True): 
            st.rerun()

    st.divider()

    col_test1, col_test2 = st.columns(2)

    with col_test1:
        st.markdown("### 發送測試訊息")
        if st.button("發送 Response 測試", key="mqtt_test_send", use_container_width=True):
            try:
                test_response = {
                    "device_id": "TEST_DEVICE",
                    "response": "a1b2c3d4e5f6" * 10 + "a1b2c3d4e5f6",
                    "timestamp": time.time(),
                    "noise_level": 3,
                    "status": "test"
                }

                # 把模擬回應直接寫入檔案
                with open(OUT_FILE, "w", encoding="utf-8") as f:
                    json.dump({"response": test_response, "received_time": time.time()}, f, ensure_ascii=False)
                
                st.success("✅ 測試訊息已儲存 (模擬)")
                st.info("請檢查下方是否出現 Response...")
            except Exception as e:
                st.error(f"❌ ERROR: {str(e)}")

    with col_test2:
        st.markdown("### 收到的訊息")
        latest_resp, _ = get_latest_response()
        if latest_resp is not None:
            st.success("✅ 已收到")
            st.json(latest_resp)
        else:
            st.warning("⏳ 未收到任何訊息")

    st.divider()
    latest_resp, _ = get_latest_response()
    if latest_resp is not None:
        st.markdown("### 收到的 Response:")
        st.json(latest_resp)
    else:
        st.info("等待 Response...")
st.divider()
    
# 顯示詳細 Response 內容
latest_resp, _ = get_latest_response()
if latest_resp is not None:
    st.markdown("### 📊 收到的 Response:")
    st.json(latest_resp)
else:
    st.info("⏳ 等待 Response...")
    st.code("# 步驟: \n1. 點擊「生成新挑戰碼」\n2. 點擊「📤 發送至 Node 端」\n3. 等待 3-5 秒\n4. 點擊「🔍 檢查並驗證」", language="python")

st.divider()

# 創建分頁
tab1, tab2, tab3, tab4 = st.tabs(["🔐 認證系統", "📊 歷史記錄", "📈 實驗統計", "⚙️ 系統狀態"])

# ═══════════════════════════════════════════════════════════════
# 【Tab 1: 認證系統】
# ═══════════════════════════════════════════════════════════════

with tab1:
    st.info(
        "📋 **系統流程說明**\n\n"
        "1️⃣ Challenge 生成：伺服器用 VRF 產生隨機挑戰碼\n"
        "2️⃣ MQTT 傳輸：挑戰碼透過 MQTT 發送到 Node 設備\n"
        "3️⃣ PUF 模擬：Node 設備模擬 PUF 特徵提取，注入雜訊\n"
        "4️⃣ Response 回傳：Node 透過 MQTT 回傳包含雜訊的響應\n"
        "5️⃣ 漢明距離驗證：伺服器計算距離，判定設備是否合法"
    )
    
    col_info, col_control = st.columns([1, 1])
    
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
            help="從 CRP 資料庫中選取的種子編號"
        )
    
    st.divider()
    
    # Phase 1: Challenge 生成與發送
    st.subheader("📤 第一階段：Challenge 生成與發送")
    
    col_gen, col_send = st.columns([1, 1])
    
    with col_gen:
        if st.button("🔄 生成新挑戰碼", key="gen_challenge"):
            try:
                c_code, proof_val = generate_vrf_challenge(sk, seed_input)
                if c_code:
                    st.session_state.current_challenge = c_code
                    st.success(f"✅ Challenge 已生成")
                    st.code(f"{c_code}", language="hex")
                    st.caption(f"Proof: {proof_val}")
            except Exception as e:
                st.error(f"❌ 生成失敗: {str(e)}")
    
    with col_send:
        if st.button("📡 發送至 Node 端", key="send_challenge"):
            if not st.session_state.current_challenge:
                st.error("請先生成 Challenge")
            else:
                try:
                    success = send_challenge_to_bridge(st.session_state.current_challenge, 3)

                    if success:
                        clear_response()
                        st.session_state.challenge_sent_time = time.time()      
                        st.success("✅ Challenge 已發送至 Bridge")
                    else:
                        st.error("❌ 發送失敗")
                except Exception as e:
                    st.error(f"❌ 發送失敗: {str(e)}")
                    print(f"[ERROR] 發送 Challenge 異常: {str(e)}")
                    import traceback
                    traceback.print_exc()
    
    st.divider()
    
    # Phase 2 & 3: 接收與驗證
    st.subheader("📥 第二/三階段：接收 Response 與驗證")
    
    col_check, col_manual = st.columns([1, 1])
    
    with col_check:
        if st.button("🔍 檢查並驗證", key="check_response"):
            if not st.session_state.current_challenge:
                st.error("❌ 請先生成 Challenge")
                print("[DEBUG] No current_challenge in session_state")
            else:
                # 從全局狀態讀取最新 Response
                latest_response, last_update_time = get_latest_response()
                print(f"[DEBUG] 檢查驗證 - 全局 Response: {latest_response is not None}, 時間: {last_update_time}")
                
                if latest_response is None:
                    # 显示详细的诊断信息
                    st.error("❌ 尚未收到 Response")
                    
                    # 诊断信息
                    with st.expander("🔧 診斷信息", expanded=True):
                        col_d1, col_d2 = st.columns(2)
                        
                        with col_d1:
                            st.markdown("**MQTT 連接狀態**")
                            st.info("ℹ️ 使用全局MQTT客戶端 (持久化)")
                        
                        with col_d2:
                            st.markdown("**等待時間**")
                            # 顯示 Challenge 發送時以來已等待多久
                            if 'challenge_sent_time' in st.session_state:
                                wait_time = time.time() - st.session_state.challenge_sent_time
                                st.warning(f"⏳ 等待中... {wait_time:.1f}秒")
                            else:
                                st.warning("尚未發送 Challenge")
                        
                        st.markdown("**可能的原因與排除步驟：**")
                        st.markdown("""
                        1. ❌ **Node 設備未運行**
                           → 執行: `python node.py`
                        
                        2. ❌ **Challenge 未成功發送**
                           → 檢查「📤 發送至 Node 端」是否顯示 ✅ 成功
                           → 如未成功，重新點擊發送
                        
                        3. ❌ **Node 處理超時**
                           → 等待 10-15 秒再試
                           → 查看 Node 終端是否有日誌
                        
                        4. ❌ **Server 未訂閱 Response 主題**
                           → 重新啟動 Streamlit: `streamlit run app.py`
                        
                        **快速診斷：**
                        ```bash
                        python mqtt_test.py
                        ```
                        """)
                    
                    print(f"[DEBUG] Global Response is None. Latest time: {last_update_time}")
                
                else:
                    try:
                        print(f"\n[DEBUG] ✅ 收到 Response！開始驗證")
                        print(f"   Device ID: {latest_response.get('device_id')}")
                        print(f"   Response: {str(latest_response.get('response'))[:40]}...")
                        
                        response_data = latest_response
                        response = response_data.get('response')
                        device_id = response_data.get('device_id', 'Unknown')
                        
                        if response:
                            hd = calculate_hamming_distance(st.session_state.current_challenge, response)
                            threshold = 5
                            
                            if hd is not None:
                                result = "pass" if hd <= threshold else "fail"
                                
                                # 保存到資料庫
                                save_auth_result(
                                    device_id=device_id,
                                    challenge=st.session_state.current_challenge,
                                    response=response,
                                    hamming_distance=hd,
                                    threshold=threshold,
                                    result=result,
                                    noise_level=response_data.get('noise_level')
                                )
                                
                                col_r1, col_r2 = st.columns(2)
                                with col_r1:
                                    st.metric("漢明距離", f"{hd} bits")
                                with col_r2:
                                    st.metric("容錯門檻", f"{threshold} bits")
                                
                                if result == "pass":
                                    st.success(f"✅ 認證通過")
                                else:
                                    st.error(f"❌ 認證失敗")
                        else:
                            st.error("❌ Response 格式無效")
                    except Exception as e:
                        st.error(f"❌ 驗證失敗: {str(e)}")
                        import traceback
                        traceback.print_exc()
    
    with col_manual:
        st.write("### 手動輸入驗證")
        manual_response = st.text_input("Response (Hex)")
        if manual_response and st.session_state.current_challenge:
            try:
                hd = calculate_hamming_distance(st.session_state.current_challenge, manual_response)
                threshold = 5
                if hd is not None:
                    st.metric("漢明距離", f"{hd} bits")
            except Exception as e:
                st.error(f"❌ {str(e)}")
    
    st.divider()
    
    # Phase 4: 批量實驗
    st.subheader("🛡️ 第四階段：容錯能力測試")
    
    if st.session_state.current_challenge:
        col_noise, col_thresh = st.columns(2)
        with col_noise:
            exp_noise = st.slider("實驗雜訊等級", 0, 20, 3)
        with col_thresh:
            exp_threshold = st.number_input("實驗容錯門檻", 0, 256, 5)
        
        if st.button("🚀 執行 100 次實驗"):
            batch_id = f"batch_{int(time.time() * 1000)}"
            
            progress_bar = st.progress(0)
            results = []
            
            try:
                for i in range(100):
                    # 注入雜訊
                    noisy_response = inject_noise(st.session_state.current_challenge, exp_noise)
                    if noisy_response is None:
                        continue
                    
                    # 計算距離
                    hd = calculate_hamming_distance(st.session_state.current_challenge, noisy_response)
                    if hd is not None:
                        result = "pass" if hd <= exp_threshold else "fail"
                        results.append({
                            'hd': hd,
                            'result': result
                        })
                        
                        # 保存到資料庫
                        save_auth_result(
                            device_id="FU_JEN_NODE_01",
                            challenge=st.session_state.current_challenge,
                            response=noisy_response,
                            hamming_distance=hd,
                            threshold=exp_threshold,
                            result=result,
                            noise_level=exp_noise,
                            batch_id=batch_id
                        )
                    
                    progress_bar.progress((i + 1) / 100)
                
                # 統計結果
                if results:
                    passed = sum(1 for r in results if r['result'] == 'pass')
                    failed = len(results) - passed
                    frr = (failed / len(results) * 100) if len(results) > 0 else 0
                    avg_hd = sum(r['hd'] for r in results) / len(results)
                    
                    # 保存批量實驗統計
                    save_batch_experiment(batch_id, exp_noise, exp_threshold, len(results), passed, failed, frr, avg_hd)
                    
                    col_s1, col_s2, col_s3 = st.columns(3)
                    with col_s1:
                        st.metric("通過", f"{passed}", "✅")
                    with col_s2:
                        st.metric("失敗", f"{failed}", "❌")
                    with col_s3:
                        st.metric("FRR", f"{frr:.1f}%", "⚠️")
                    
                    st.success(f"✅ 實驗完成！(Batch ID: {batch_id})")
            except Exception as e:
                st.error(f"❌ 實驗執行失敗: {str(e)}\n{traceback.format_exc()}")
    else:
        st.warning("⏳ 請先生成 Challenge")

# ═══════════════════════════════════════════════════════════════
# 【Tab 2: 歷史記錄】
# ═══════════════════════════════════════════════════════════════

with tab2:
    st.subheader("📋 認證歷史記錄")
    
    col_f1, col_f2, col_f3 = st.columns(3)
    with col_f1:
        limit = st.number_input("顯示筆數", 10, 1000, 100)
    with col_f2:
        filter_device = st.selectbox("筛選設備", ["全部", "FU_JEN_NODE_01"])
    with col_f3:
        filter_result = st.selectbox("篩選結果", ["全部", "pass", "fail"])
    
    # 取得記錄
    df = get_auth_history(limit=limit)
    
    if not df.empty:
        # 應用篩選
        if filter_device != "全部":
            df = df[df['device_id'] == filter_device]
        if filter_result != "全部":
            df = df[df['result'] == filter_result]
        
        st.dataframe(df, use_container_width=True)
        
        # 下載 CSV
        csv_data = df.to_csv(index=False)
        st.download_button(
            label="📥 下載為 CSV",
            data=csv_data,
            file_name=f"auth_history_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv"
        )
    else:
        st.info("📭 暫無認證歷史記錄")

# ═══════════════════════════════════════════════════════════════
# 【Tab 3: 實驗統計】
# ═══════════════════════════════════════════════════════════════

with tab3:
    st.subheader("📈 批量實驗統計")
    
    batch_df = get_all_batch_experiments(limit=50)
    
    if not batch_df.empty:
        # 顯示統計表格
        st.dataframe(batch_df, use_container_width=True)
        
        # 統計圖表
        col_chart1, col_chart2 = st.columns(2)
        
        with col_chart1:
            st.bar_chart(batch_df[['batch_id', 'frr']].set_index('batch_id'))
        
        with col_chart2:
            st.line_chart(batch_df[['timestamp', 'avg_distance']].set_index('timestamp'))
    else:
        st.info("📭 暫無批量實驗記錄")

# ═══════════════════════════════════════════════════════════════
# 【Tab 4: 系統狀態】
# ═══════════════════════════════════════════════════════════════

with tab4:
    st.subheader("⚙️ 系統監控")
    
    col_status1, col_status2, col_status3 = st.columns(3)
    
    with col_status1:
        st.metric("Bridge 狀態", "🟢 IPC 啟用中")
    
    with col_status2:
        db_size = os.path.getsize(DB_PATH) / 1024 if os.path.exists(DB_PATH) else 0
        st.metric("數據庫大小", f"{db_size:.1f} KB")
    
    with col_status3:
        hist_count = len(get_auth_history(limit=100000))
        st.metric("認證記錄數", f"{hist_count}")
    
    pass
    pass
    
    st.divider()
    st.write("**📊 系統資訊**")
    st.code(f"""
MQTT Broker: broker.emqx.io:1883
Challenge Topic: fujen/iot/challenge
Response Topic: fujen/iot/response
Database: {DB_PATH}
Python Version: 3.8+
    """)

st.divider()
st.markdown("---\n*IoT 硬體指紋認證系統 v2.0 (Enhanced)*\n*最後更新: 2026-03-29*")
