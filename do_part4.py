with open('app.py', 'r', encoding='utf-8') as f:
    text = f.read()

# I will replace the main MQTT panel layout entirely
s_idx = text.find('with st.expander(')
e_idx = text.find('st.divider()', s_idx + 1)
e_idx = text.find('st.divider()', e_idx + 1)

new_panel = """with st.expander("Bridge 連線狀態與測試", expanded=True):
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
"""
if s_idx != -1 and e_idx != -1:
    text = text[:s_idx] + new_panel + text[e_idx:]

# Next: the challenge send section
s_idx2 = text.find('if not st.session_state.current_challenge:', text.find('send_challenge'))
if s_idx2 != -1:
    e_idx2 = text.find('except Exception as e:', s_idx2)
    new_chal = """if not st.session_state.current_challenge:
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
                """
    if e_idx2 != -1:
        text = text[:s_idx2] + new_chal + text[e_idx2:]

# Status section tab4
s_idx3 = text.find('        mqtt_icon =')
if s_idx3 != -1:
    e_idx3 = text.find(']', s_idx3)
    text = text[:s_idx3] + '        st.metric("Bridge 狀態", "🟢 IPC 啟用中")\n' + text[e_idx3+1:]

with open('app.py', 'w', encoding='utf-8') as f:
    f.write(text)

