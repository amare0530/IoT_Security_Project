"""
MQTT bridge between Streamlit app and simulated IoT node.

This process exists because `app.py` currently uses local JSON files for IPC
instead of talking to MQTT directly:

- Reads `challenge_out.json` written by `app.py`
- Publishes challenge to MQTT topic
- Receives response from MQTT topic
- Writes `response_in.json` for `app.py`

It also updates `bridge_status.json` as a heartbeat so UI can show bridge health.
"""

import json
import os
import socket
import sys
import time

import paho.mqtt.client as mqtt

BROKER = "broker.emqx.io"
PORT = 1883
KEEPALIVE = 60
CONNECT_RETRY_SECONDS = 3
POLL_INTERVAL_SECONDS = 0.5

TOPIC_CHALLENGE = "fujen/iot/challenge"
TOPIC_RESPONSE = "fujen/iot/response"

OUT_FILE = "response_in.json"
IN_FILE = "challenge_out.json"
HEARTBEAT_FILE = "bridge_status.json"

last_challenge_time = 0
bridge_connected = False
_instance_lock_socket = None


def enforce_single_instance(lock_port=45831):
    """Prevent duplicate bridge processes that would race on IPC files."""
    lock_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        lock_socket.bind(("127.0.0.1", lock_port))
        lock_socket.listen(1)
        return lock_socket
    except OSError:
        print(" [Bridge] 偵測到另一個 mqtt_bridge.py 已在執行，請先關閉重複實例")
        sys.exit(1)


def write_heartbeat(extra_message=""):
    """讓 app.py 能判斷 Bridge 是否仍存活且已連線。"""
    data = {
        "last_seen": time.time(),
        "connected": bridge_connected,
        "broker": BROKER,
        "message": extra_message,
    }
    try:
        with open(HEARTBEAT_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f" [Bridge] 寫入心跳檔失敗: {e}")


def on_connect(client, userdata, flags, rc):
    global bridge_connected
    if rc == 0:
        bridge_connected = True
        print(f" [Bridge] 已成功連接到 MQTT Broker ({BROKER})")
        client.subscribe(TOPIC_RESPONSE, qos=1)
        print(f" [Bridge] 已訂閱主題: {TOPIC_RESPONSE}")
        write_heartbeat("connected")
    else:
        bridge_connected = False
        print(f" [Bridge] 連接失敗，代碼: {rc}")
        write_heartbeat(f"connect failed: {rc}")


def on_disconnect(client, userdata, rc):
    global bridge_connected
    bridge_connected = False
    print(f" [Bridge] MQTT 連線中斷 (rc={rc})")
    write_heartbeat(f"disconnected: {rc}")


def on_message(client, userdata, msg):
    print(f" [Bridge] 收到 MQTT 訊息 (Topic: {msg.topic})")
    try:
        payload = json.loads(msg.payload.decode("utf-8"))
        print(f"   Payload: {str(payload)[:100]}...")

        # 寫入檔案供 Streamlit 讀取
        with open(OUT_FILE, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "response": payload,
                    "received_time": time.time(),
                },
                f,
                ensure_ascii=False,
                indent=2,
            )

        print(f" [Bridge] 已將 Response 寫入 {OUT_FILE}")
        write_heartbeat("response forwarded")
    except Exception as e:
        print(f" [Bridge] 處理訊息錯誤: {e}")
        write_heartbeat(f"message error: {e}")


def ensure_ipc_files():
    """Create IPC files on startup so first read does not fail."""
    if not os.path.exists(OUT_FILE):
        with open(OUT_FILE, "w", encoding="utf-8") as f:
            json.dump({}, f)

    if not os.path.exists(IN_FILE):
        with open(IN_FILE, "w", encoding="utf-8") as f:
            json.dump({}, f)


client = mqtt.Client(client_id=f"IoT_Bridge_{int(time.time())}")
client.on_connect = on_connect
client.on_disconnect = on_disconnect
client.on_message = on_message
client.reconnect_delay_set(min_delay=1, max_delay=30)

print("啟動 MQTT Bridge 服務中...")

try:
    _instance_lock_socket = enforce_single_instance()
    ensure_ipc_files()
    write_heartbeat("starting")

    print(f" [Bridge] 正在連線 {BROKER}:{PORT} ...")
    client.connect_async(BROKER, PORT, KEEPALIVE)
    client.loop_start()
    print(" [Bridge] MQTT 背景監聽已啟動")

    # Poll file-based command channel and forward only newer challenge events.
    while True:
        try:
            if os.path.exists(IN_FILE):
                with open(IN_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)

                cmd_time = data.get("timestamp", 0)
                if cmd_time > last_challenge_time:
                    print("\n [Bridge] 偵測到新的 Challenge 任務，準備發送...")
                    payload_to_send = json.dumps(
                        {
                            "challenge": data.get("challenge"),
                            "noise_level": data.get("noise_level", 3),
                            "timestamp": cmd_time,
                            "nonce": data.get("nonce"),
                            "max_response_time": data.get("max_response_time", 10),
                            "challenge_source": data.get("challenge_source", "vrf"),
                            "dataset_name": data.get("dataset_name"),
                            "target_device_id": data.get("target_device_id"),
                            "target_session_id": data.get("target_session_id"),
                            "target_timestamp": data.get("target_timestamp"),
                        }
                    )

                    result = client.publish(TOPIC_CHALLENGE, payload_to_send, qos=1)
                    if result.rc == mqtt.MQTT_ERR_SUCCESS:
                        print(" [Bridge] Challenge 已透過 MQTT 成功發送")
                        last_challenge_time = cmd_time

                        # 清空目前的 response_in.json，等待新回應
                        with open(OUT_FILE, "w", encoding="utf-8") as rf:
                            json.dump({}, rf)

                        write_heartbeat("challenge forwarded")
                    else:
                        print(f" [Bridge] 發送 Challenge 失敗，代碼: {result.rc}")
                        write_heartbeat(f"publish failed: {result.rc}")

        except json.JSONDecodeError:
            # 檔案正在寫入中，下一輪再讀
            pass
        except Exception as e:
            print(f" [Bridge] 輪詢迴圈錯誤: {e}")
            write_heartbeat(f"loop error: {e}")

        write_heartbeat("running")
        time.sleep(POLL_INTERVAL_SECONDS)

except KeyboardInterrupt:
    print("\n 停止 MQTT Bridge...")
finally:
    try:
        client.loop_stop()
        client.disconnect()
    except Exception:
        pass
    try:
        if _instance_lock_socket:
            _instance_lock_socket.close()
    except Exception:
        pass
    print(" [Bridge] 已結束")



