with open('app.py', 'r', encoding='utf-8') as f: text = f.read()

import re
text = re.sub(r'if "response_queue" not in st\.session_state:\n    st\.session_state\.response_queue = Queue\(\)', '', text)
text = text.replace('if "latest_mqtt_response" not in st.session_state:\n    st.session_state.latest_mqtt_response = None\n', '')
text = text.replace('if "mqtt_listener_started" not in st.session_state:\n    st.session_state.mqtt_listener_started = False\n', '')
text = text.replace('if "mqtt_status" not in st.session_state:\n    st.session_state.mqtt_status = "未連線"\n', '')
text = text.replace('if "mqtt_error" not in st.session_state:\n    st.session_state.mqtt_error = None\n', '')

with open('app.py', 'w', encoding='utf-8') as f: f.write(text)