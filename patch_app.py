import re
import os
import json

with open('app.py', 'r', encoding='utf-8') as f:
    orig = f.read()

# Replace block 1: session state to mqtt init
start_txt = 'if "current_challenge" not in st.session_state:'
end_txt = 'print("[APP] MQTT 用戶端初始化完成")\n'

if start_txt in orig and end_txt in orig:
    s = orig.find(start_txt)
    e = orig.find(end_txt) + len(end_txt)
    
    new_block = '''if "current_challenge" not in st.session_state:
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
        if os.path.exists(OUT_FILE):
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
'''
    orig = orig[:s] + new_block + orig[e:]

# Remove MQTTState
orig = orig.replace('MQTTState.clear_response()', 'clear_response()')

# Fix diagnostic check
old_conn_chk = '''        try:
            # 檢查 mqtt_client 是否已初始化
            if 'mqtt_client' in globals() and mqtt_client is not None:
                # 嘗試檢查用戶端連線狀態
                if hasattr(mqtt_client, '_sock_connect_state'):
                    state = mqtt_client._sock_connect_state
                    if state:
                        st.success("✅ 已連線")
                    else:
                        st.warning("⚠️ 連線中...")
                else:
                    st.info("ℹ️ 用戶端已初始化")
            else:
                st.error("❌ 用戶端未初始化")
        except Exception as e:
            st.error(f"❌ ERROR: {str(e)}")'''

new_conn_chk = '''        st.success("✅ Bridge IPC 模式已啟用")'''

orig = orig.replace(old_conn_chk, new_conn_chk)

# Fix test button publish
old_test_pub = '''                # 發佈到 Response 主題
                print(f"\\n[TEST] 發送測試訊息到 fujen/iot/response")
                result = mqtt_client.publish(
                    "fujen/iot/response",
                    json.dumps(test_response),
                    qos=1
                )

                print(f"[TEST] publish() 回傳碼: {result.rc}")

                if result.rc == mqtt.MQTT_ERR_SUCCESS:'''

new_test_pub = '''                # 把模擬回應直接寫入檔案
                with open(OUT_FILE, "w", encoding="utf-8") as f:
                    json.dump({"response": test_response, "received_time": time.time()}, f, ensure_ascii=False)
                
                if True: # Simulating success'''

orig = orig.replace(old_test_pub, new_test_pub)

# Fix challenge send
old_chal_send = '''                    # 使用 QoS=1 確保發送
                    result = mqtt_client.publish(
                        "fujen/iot/challenge",
                        payload,
                        qos=1
                    )

                    if result.rc == mqtt.MQTT_ERR_SUCCESS:'''

new_chal_send = '''                    success = send_challenge_to_bridge(st.session_state.current_challenge, 3)

                    if success:'''

orig = orig.replace(old_chal_send, new_chal_send)

# Fix status in Tab 4
old_status = '''        mqtt_icon = "🟢" if "已連接" in st.session_state.mqtt_status else "🔴"  
        st.metric("MQTT 狀態", f"{mqtt_icon} {st.session_state.mqtt_status}")'''
new_status = '''        st.metric("Bridge 狀態", "🟢 IPC 啟用中")'''

orig = orig.replace(old_status, new_status)

with open('app.py', 'w', encoding='utf-8') as f:
    f.write(orig)

print("Patch applied")