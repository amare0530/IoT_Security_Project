"""
═══════════════════════════════════════════════════════════════════
IoT 硬體指紋認證系統 - Streamlit 伺服器端 (Server)
增強版本 - 整合 SQLite 資料庫與完善異常處理
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
from ui_theme import inject_theme, render_status_badge

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

OUT_FILE = "response_in.json"
IN_FILE = "challenge_out.json"
HEARTBEAT_FILE = "bridge_status.json"
RESPONSE_WAIT_TIMEOUT = 15
RESPONSE_POLL_INTERVAL = 0.5

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
        st.error(f"發送 Challenge 失敗: {e}")
        return False

def get_bridge_status():
    """讀取 Bridge 心跳檔，回傳 (is_healthy, status_message, age_seconds)。"""
    if not os.path.exists(HEARTBEAT_FILE):
        return False, "尚未偵測到 Bridge，請先啟動 `python mqtt_bridge.py`", None

    try:
        with open(HEARTBEAT_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

        last_seen = float(data.get("last_seen", 0))
        connected = bool(data.get("connected", False))
        age = time.time() - last_seen if last_seen else None

        if age is None or age > 5:
            return False, "Bridge 心跳逾時，請檢查 Bridge 視窗是否仍在執行", age

        if not connected:
            return False, "Bridge 已啟動，但尚未連上 MQTT Broker", age

        return True, "Bridge 與 MQTT 連線正常", age
    except Exception as e:
        return False, f"Bridge 狀態檔讀取失敗: {e}", None

def wait_for_latest_response(timeout_seconds=RESPONSE_WAIT_TIMEOUT, poll_interval=RESPONSE_POLL_INTERVAL):
    """在限定時間內輪詢 Response 檔案，避免單次讀取造成誤判。"""
    sent_time = st.session_state.get("challenge_sent_time", time.time())
    deadline = time.time() + timeout_seconds

    while time.time() < deadline:
        latest_response, last_update_time = get_latest_response()
        if latest_response is not None and last_update_time is not None and last_update_time >= sent_time:
            return latest_response, last_update_time
        time.sleep(poll_interval)

    return None, None


def get_auth_count():
    """取得認證歷史總筆數。"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM auth_history")
        total = cursor.fetchone()[0]
        conn.close()
        return total
    except Exception:
        return 0


def verify_response_payload(challenge, response_data, threshold=5, persist=True):
    """驗證 response payload，必要時寫入資料庫並回傳結果字典。"""
    response = response_data.get("response") if isinstance(response_data, dict) else None
    device_id = response_data.get("device_id", "Unknown") if isinstance(response_data, dict) else "Unknown"

    if not response:
        return None

    hd = calculate_hamming_distance(challenge, response)
    if hd is None:
        return None

    result = "pass" if hd <= threshold else "fail"

    if persist:
        save_auth_result(
            device_id=device_id,
            challenge=challenge,
            response=response,
            hamming_distance=hd,
            threshold=threshold,
            result=result,
            noise_level=response_data.get("noise_level") if isinstance(response_data, dict) else None,
        )

    return {
        "device_id": device_id,
        "hamming_distance": hd,
        "threshold": threshold,
        "result": result,
        "response": response,
    }


if "current_proof" not in st.session_state:
    st.session_state.current_proof = None
if "challenge_sent_time" not in st.session_state:
    st.session_state.challenge_sent_time = None
if "last_verify_result" not in st.session_state:
    st.session_state.last_verify_result = None
if "last_verified_received_time" not in st.session_state:
    st.session_state.last_verified_received_time = None


inject_theme()

st.markdown(
    """
<div class="hero-panel">
  <h1 class="hero-title">IoT 設備硬體指紋認證系統</h1>
  <p class="hero-subtitle">更簡潔的操作流程：一鍵驗證、即時狀態、進階工具分區管理</p>
</div>
""",
    unsafe_allow_html=True,
)

bridge_ok, bridge_msg, bridge_age = get_bridge_status()
latest_resp, latest_resp_time = get_latest_response()
latest_resp_age = (time.time() - latest_resp_time) if latest_resp_time else None
history_count = get_auth_count()

status_cols = st.columns(4)
with status_cols[0]:
    st.markdown(
        render_status_badge(
            "Bridge 狀態",
            "正常" if bridge_ok else "異常",
            bridge_ok,
            bridge_msg,
        ),
        unsafe_allow_html=True,
    )

with status_cols[1]:
    st.markdown(
        render_status_badge(
            "最新 Response",
            "已收到" if latest_resp is not None else "尚未收到",
            latest_resp is not None,
            f"約 {latest_resp_age:.1f} 秒前" if latest_resp_age is not None else "等待中",
        ),
        unsafe_allow_html=True,
    )

with status_cols[2]:
    st.markdown(
        render_status_badge(
            "認證歷史",
            f"{history_count} 筆",
            history_count > 0,
            "已保存於 SQLite",
        ),
        unsafe_allow_html=True,
    )

last_result = st.session_state.last_verify_result
with status_cols[3]:
    st.markdown(
        render_status_badge(
            "最近驗證",
            "通過" if last_result and last_result.get("result") == "pass" else ("失敗" if last_result else "尚未驗證"),
            bool(last_result and last_result.get("result") == "pass"),
            f"HD={last_result['hamming_distance']}" if last_result else "等待操作",
        ),
        unsafe_allow_html=True,
    )

with st.sidebar:
    st.header("控制面板")
    sk = st.text_input(
        "伺服器私鑰",
        value="FU_JEN_CSIE_SECRET_2026",
        type="password",
        help="用於生成 VRF Challenge",
    )
    seed_input = st.text_input(
        "CRP 種子",
        value="CRP_INDEX_001",
        help="相同種子會得到相同 Challenge",
    )
    send_noise_level = st.slider("發送雜訊等級", 0, 20, 3)
    verify_threshold = st.slider("驗證門檻", 1, 32, 5)

    st.markdown("<div class='section-divider'></div>", unsafe_allow_html=True)
    if st.button("清空 Response 快取", use_container_width=True):
        clear_response()
        st.success("已清空 response_in.json")
    if st.button("刷新 UI", use_container_width=True):
        st.rerun()


def update_verification_state(verify_result, received_time):
    st.session_state.last_verify_result = verify_result
    st.session_state.last_verified_received_time = received_time


def verify_latest_response(threshold):
    if not st.session_state.current_challenge:
        st.error("❌ 尚未生成 Challenge")
        return

    with st.spinner("⏳ 等待 Node 回應中..."):
        latest_response, recv_time = wait_for_latest_response()

    if latest_response is None:
        latest_response, recv_time = get_latest_response()

    if latest_response is None:
        st.error("❌ 尚未收到 Response")
        st.info("請確認 Node 與 Bridge 都在執行中")
        return

    if recv_time is not None and recv_time == st.session_state.last_verified_received_time:
        st.info("ℹ️ 這筆 Response 已驗證過，未重複寫入資料庫")
        return

    verify_result = verify_response_payload(
        challenge=st.session_state.current_challenge,
        response_data=latest_response,
        threshold=threshold,
        persist=True,
    )
    if verify_result:
        update_verification_state(verify_result, recv_time)


action_cols = st.columns(4)
with action_cols[0]:
    run_one_click = st.button("🚀 一鍵驗證", use_container_width=True, type="primary")
with action_cols[1]:
    run_generate = st.button("1. 生成 Challenge", use_container_width=True)
with action_cols[2]:
    run_send = st.button("2. 發送 Challenge", use_container_width=True)
with action_cols[3]:
    run_check = st.button("3. 驗證最新回應", use_container_width=True)

if run_generate:
    challenge, proof = generate_vrf_challenge(sk, seed_input)
    if challenge:
        st.session_state.current_challenge = challenge
        st.session_state.current_proof = proof
        st.success("✅ Challenge 已生成")

if run_send:
    if not st.session_state.current_challenge:
        st.error("❌ 請先生成 Challenge")
    else:
        clear_response()
        sent_ok = send_challenge_to_bridge(st.session_state.current_challenge, send_noise_level)
        if sent_ok:
            st.session_state.challenge_sent_time = time.time()
            st.success("✅ Challenge 已發送")
        else:
            st.error("❌ 發送失敗")

if run_check:
    verify_latest_response(verify_threshold)

if run_one_click:
    challenge, proof = generate_vrf_challenge(sk, seed_input)
    if challenge:
        st.session_state.current_challenge = challenge
        st.session_state.current_proof = proof
        clear_response()
        sent_ok = send_challenge_to_bridge(challenge, send_noise_level)
        if sent_ok:
            st.session_state.challenge_sent_time = time.time()
            verify_latest_response(verify_threshold)
        else:
            st.error("❌ 發送失敗，無法完成一鍵驗證")

st.divider()

latest_resp, latest_resp_time = get_latest_response()

st.subheader("最近一次驗證結果")
latest_result = st.session_state.last_verify_result
if latest_result:
    r1, r2, r3, r4 = st.columns(4)
    with r1:
        st.metric("結果", "✅ 通過" if latest_result["result"] == "pass" else "❌ 失敗")
    with r2:
        st.metric("漢明距離", f"{latest_result['hamming_distance']} bits")
    with r3:
        st.metric("門檻", f"{latest_result['threshold']} bits")
    with r4:
        st.metric("設備 ID", latest_result["device_id"])

    if latest_result["result"] == "pass":
        st.success("認證成功：設備特徵符合預期")
    else:
        st.error("認證失敗：距離超過門檻")
else:
    st.info("尚未有驗證結果，請先使用一鍵驗證或步驟操作")

info_left, info_right = st.columns(2)
with info_left:
    st.markdown("### 當前 Challenge")
    if st.session_state.current_challenge:
        st.code(st.session_state.current_challenge, language="text")
        if st.session_state.current_proof:
            st.caption(f"Proof: {st.session_state.current_proof}")
    else:
        st.info("尚未生成 Challenge")

with info_right:
    st.markdown("### 最新 Response")
    if latest_resp is not None:
        st.json(latest_resp)
    else:
        st.info("尚未收到 Response")

with st.expander("進階工具：手動輸入驗證（選用）", expanded=False):
    manual_response = st.text_input("Response (Hex)", key="manual_response_hex")
    if manual_response and st.session_state.current_challenge:
        hd = calculate_hamming_distance(st.session_state.current_challenge, manual_response)
        if hd is not None:
            st.metric("手動驗證漢明距離", f"{hd} bits")

tab_batch, tab_history, tab_monitor = st.tabs(["🛡️ 批量實驗", "📊 歷史記錄", "⚙️ 系統監控"])

with tab_batch:
    st.subheader("容錯能力測試（100 次）")
    if st.session_state.current_challenge:
        c1, c2 = st.columns(2)
        with c1:
            exp_noise = st.slider("實驗雜訊等級", 0, 20, 3, key="batch_noise")
        with c2:
            exp_threshold = st.number_input("實驗容錯門檻", 0, 256, 5, key="batch_threshold")

        if st.button("🚀 執行 100 次實驗", key="run_batch"):
            batch_id = f"batch_{int(time.time() * 1000)}"
            progress_bar = st.progress(0)
            results = []

            try:
                for i in range(100):
                    noisy_response = inject_noise(st.session_state.current_challenge, exp_noise)
                    if noisy_response is None:
                        continue

                    hd = calculate_hamming_distance(st.session_state.current_challenge, noisy_response)
                    if hd is not None:
                        result = "pass" if hd <= exp_threshold else "fail"
                        results.append({"hd": hd, "result": result})
                        save_auth_result(
                            device_id="FU_JEN_NODE_01",
                            challenge=st.session_state.current_challenge,
                            response=noisy_response,
                            hamming_distance=hd,
                            threshold=exp_threshold,
                            result=result,
                            noise_level=exp_noise,
                            batch_id=batch_id,
                        )

                    progress_bar.progress((i + 1) / 100)

                if results:
                    passed = sum(1 for item in results if item["result"] == "pass")
                    failed = len(results) - passed
                    frr = (failed / len(results) * 100) if results else 0
                    avg_hd = sum(item["hd"] for item in results) / len(results)
                    save_batch_experiment(batch_id, exp_noise, exp_threshold, len(results), passed, failed, frr, avg_hd)

                    s1, s2, s3 = st.columns(3)
                    with s1:
                        st.metric("通過", f"{passed}")
                    with s2:
                        st.metric("失敗", f"{failed}")
                    with s3:
                        st.metric("FRR", f"{frr:.1f}%")

                    st.success(f"✅ 實驗完成（Batch ID: {batch_id}）")
            except Exception as e:
                st.error(f"❌ 實驗執行失敗: {str(e)}\n{traceback.format_exc()}")
    else:
        st.warning("請先生成 Challenge 再執行批量實驗")

with tab_history:
    st.subheader("認證歷史記錄")
    f1, f2, f3 = st.columns(3)
    with f1:
        limit = st.number_input("顯示筆數", 10, 1000, 100, key="history_limit")
    with f2:
        filter_device = st.selectbox("篩選設備", ["全部", "FU_JEN_NODE_01"], key="history_device")
    with f3:
        filter_result = st.selectbox("篩選結果", ["全部", "pass", "fail"], key="history_result")

    df = get_auth_history(limit=limit)
    if not df.empty:
        if filter_device != "全部":
            df = df[df["device_id"] == filter_device]
        if filter_result != "全部":
            df = df[df["result"] == filter_result]

        st.dataframe(df, use_container_width=True)
        csv_data = df.to_csv(index=False)
        st.download_button(
            label="📥 下載 CSV",
            data=csv_data,
            file_name=f"auth_history_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv",
        )
    else:
        st.info("暫無認證歷史記錄")

with tab_monitor:
    st.subheader("系統監控與診斷")
    m1, m2, m3 = st.columns(3)
    with m1:
        st.metric("Bridge", "正常" if bridge_ok else "異常")
    with m2:
        db_size = os.path.getsize(DB_PATH) / 1024 if os.path.exists(DB_PATH) else 0
        st.metric("資料庫大小", f"{db_size:.1f} KB")
    with m3:
        st.metric("認證記錄數", f"{history_count}")

    hb_exists = os.path.exists(HEARTBEAT_FILE)
    if hb_exists:
        try:
            with open(HEARTBEAT_FILE, "r", encoding="utf-8") as f:
                heartbeat = json.load(f)
            st.caption("Bridge 心跳狀態")
            st.json(heartbeat)
        except Exception as e:
            st.error(f"讀取心跳檔失敗: {e}")
    else:
        st.warning("尚未找到 bridge_status.json")

    diag_col1, diag_col2 = st.columns(2)
    with diag_col1:
        if st.button("寫入模擬 Response", key="monitor_mock_response", use_container_width=True):
            mock_response = {
                "device_id": "TEST_DEVICE",
                "response": "a1b2c3d4e5f6" * 10 + "a1b2c3d4e5f6",
                "timestamp": time.time(),
                "noise_level": 3,
                "status": "test",
            }
            with open(OUT_FILE, "w", encoding="utf-8") as f:
                json.dump({"response": mock_response, "received_time": time.time()}, f, ensure_ascii=False, indent=2)
            st.success("已寫入模擬 Response")
    with diag_col2:
        st.code(
            """
Broker: broker.emqx.io:1883
Challenge Topic: fujen/iot/challenge
Response Topic: fujen/iot/response
IPC Files: challenge_out.json / response_in.json / bridge_status.json
""".strip(),
            language="text",
        )

st.markdown("---")
st.caption("IoT 硬體指紋認證系統 - 簡化介面版")
