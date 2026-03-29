import re

with open('app.py', 'r', encoding='utf-8') as f:
    text = f.read()

# We need to find the MQTT block and replace it
# from 'if "current_challenge" not in st.session_state:' to 'print("[APP] MQTT ...")'

start_idx = text.find('if "current_challenge" not in st.session_state:')
end_str = 'print("[APP] MQTT 用戶端初始化完成")'
end_idx = text.find(end_str)

if start_idx != -1 and end_idx != -1:
    end_idx += len(end_str)
    
    new_block = '''if "current_challenge" not in st.session_state:
    st.session_state.current_challenge = None

if "bridge_status" not in st.session_state:
    st.session_state.bridge_status = "未知"

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
'''
    text = text[:start_idx] + new_block + text[end_idx:]
    
    # Also replace mqtt_client.publish references
    
    # In Send Challenge testing block
    text = text.replace('result = mqtt_client.publish(\n                        "fujen/iot/challenge",\n                        payload,\n                        qos=1\n                    )\n\n                    if result.rc == mqtt.MQTT_ERR_SUCCESS:', 'success = send_challenge_to_bridge(st.session_state.current_challenge, 3)\n\n                    if success:')
    
    # In diagnostic publish block
    test_block_old = '''result = mqtt_client.publish(
                    "fujen/iot/response",
                    json.dumps(test_response),
                    qos=1
                )'''
    test_block_new = '''# 把模擬回應直接寫入檔案
                with open(OUT_FILE, "w", encoding="utf-8") as f:
                    json.dump({"response": test_response, "received_time": time.time()}, f)
                result = type('obj', (object,), {'rc': 0})()'''
    text = text.replace(test_block_old, test_block_new)

    # In status block
    text = text.replace('mqtt_icon = "??" if "已連接" in st.session_state.mqtt_status else "??"\n        st.metric("MQTT 狀態", f"{mqtt_icon} {st.session_state.mqtt_status}")', 'st.metric("Bridge 狀態", "?? 已啟動 (監控中)")')

    with open('app.py', 'w', encoding='utf-8') as f:
        f.write(text)
    print("app.py successfully fixed")
else:
    print("Could not find start/end bounds")
