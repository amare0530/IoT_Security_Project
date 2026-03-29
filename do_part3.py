import re

with open('app.py', 'r', encoding='utf-8') as f:
    orig = f.read()

# Replace mqtt connection check
old_chk = '''        try:
            # 瑼Ｘ mqtt_client ?臬撌脣?憪?
            if 'mqtt_client' in globals() and mqtt_client is not None:
                # ?岫瑼Ｘ摰Ｘ蝡舀?阡?
                if hasattr(mqtt_client, '_sock_connect_state'):
                    state = mqtt_client._sock_connect_state
                    if state:
                        st.success("??撌脤?")
                    else:
                        st.warning("?? ??銝?..")
                else:
                    st.info("?對? 摰Ｘ蝡臬歇????)
            else:
                st.error("??摰Ｘ蝡舀????)
        except Exception as e:
            st.error(f"??ERROR: {str(e)}")'''
# Since mojibake makes regex hard, we'll just replace the whole expander block
# Find everything between "with st.expander" and "st.divider()"
start_exp = orig.find('with st.expander("?妒 MQTT ??閮箸 (撖行?皜祈岫)", expanded=True):')
if start_exp != -1:
    end_exp = orig.find('    st.divider()', start_exp)

    new_exp = '''with st.expander("Bridge 連線狀態與測試", expanded=True):
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

'''
    if end_exp != -1:
        orig = orig[:start_exp] + new_exp + orig[end_exp:]

# Next: test button publish
start_test = orig.find('                # ?潮 Response 銝駁?')
if start_test != -1:
    end_test = orig.find('            except Exception as e:', start_test)
    new_test = '''                with open(OUT_FILE, "w", encoding="utf-8") as f:
                    json.dump({"response": test_response, "received_time": time.time()}, f, ensure_ascii=False)
                st.success("✅ 測試訊息已儲存 (模擬)")
                st.info("請檢查下方是否出現 Response...")
'''
    orig = orig[:start_test] + new_test + orig[end_test:]

# Next: challenge send
# '                    # 雿輻 QoS=1 靽???'
start_pub = orig.find('                    # 雿輻 QoS=1 靽???')
if start_pub != -1:
    end_pub = orig.find('                except Exception as e:', start_pub)
    new_pub = '''                    success = send_challenge_to_bridge(st.session_state.current_challenge, 3)

                    if success:
                        clear_response()
                        st.session_state.challenge_sent_time = time.time()      
                        st.success("✅ Challenge 已發送至 Bridge")
                    else:
                        st.error("❌ 發送失敗")
'''
    orig = orig[:start_pub] + new_pub + orig[end_pub:]

# Next metric status
start_met = orig.find('        mqtt_icon =')
if start_met != -1:
    end_met = orig.find('        st.metric(', start_met) + 30 # roughly covering it
    end_met = orig.find('\n', end_met)
    new_met = '        st.metric("Bridge 狀態", "🟢 IPC 啟用中")'
    orig = orig[:start_met] + new_met + orig[end_met:]

with open('app.py', 'w', encoding='utf-8') as f:
    f.write(orig)

print("Fix applied")