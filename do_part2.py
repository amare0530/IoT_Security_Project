with open('app.py', 'r', encoding='utf-8') as f: lines = f.readlines()

new_lines = '''if "current_challenge" not in st.session_state:
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

'''

with open('app.py', 'w', encoding='utf-8') as f: 
    f.writelines(lines[:295])
    f.write(new_lines)
    f.writelines(lines[465:])
