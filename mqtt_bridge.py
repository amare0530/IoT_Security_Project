import json
import os
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
        print(f"⚠️ [Bridge] 寫入心跳檔失敗: {e}")


def on_connect(client, userdata, flags, rc):
    global bridge_connected
    if rc == 0:
        bridge_connected = True
        print(f"✅ [Bridge] 已成功連接到 MQTT Broker ({BROKER})")
        client.subscribe(TOPIC_RESPONSE, qos=1)
        print(f"✅ [Bridge] 已訂閱主題: {TOPIC_RESPONSE}")
        write_heartbeat("connected")
    else:
        bridge_connected = False
        print(f"❌ [Bridge] 連接失敗，代碼: {rc}")
        write_heartbeat(f"connect failed: {rc}")


def on_disconnect(client, userdata, rc):
    global bridge_connected
    bridge_connected = False
    print(f"⚠️ [Bridge] MQTT 連線中斷 (rc={rc})")
    write_heartbeat(f"disconnected: {rc}")


def on_message(client, userdata, msg):
    print(f"📥 [Bridge] 收到 MQTT 訊息 (Topic: {msg.topic})")
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

        print(f"✅ [Bridge] 已將 Response 寫入 {OUT_FILE}")
        write_heartbeat("response forwarded")
    except Exception as e:
        print(f"❌ [Bridge] 處理訊息錯誤: {e}")
        write_heartbeat(f"message error: {e}")


def ensure_ipc_files():
    if not os.path.exists(OUT_FILE):
        with open(OUT_FILE, "w", encoding="utf-8") as f:
            json.dump({}, f)

    if not os.path.exists(IN_FILE):
        with open(IN_FILE, "w", encoding="utf-8") as f:
            json.dump({}, f)


def connect_with_retry(client):
    """連線失敗時持續重試，直到成功或被中斷。"""
    while True:
        try:
            print(f"🔌 [Bridge] 正在連線 {BROKER}:{PORT} ...")
            client.connect(BROKER, PORT, KEEPALIVE)
            return
        except KeyboardInterrupt:
            raise
        except Exception as e:
            print(f"❌ [Bridge] 連線失敗: {e}，{CONNECT_RETRY_SECONDS} 秒後重試")
            write_heartbeat(f"connect retry: {e}")
            time.sleep(CONNECT_RETRY_SECONDS)


client = mqtt.Client(client_id=f"IoT_Bridge_{int(time.time())}")
client.on_connect = on_connect
client.on_disconnect = on_disconnect
client.on_message = on_message

print("啟動 MQTT Bridge 服務中...")

try:
    ensure_ipc_files()
    write_heartbeat("starting")

    connect_with_retry(client)
    client.loop_start()
    print("✅ [Bridge] MQTT 背景監聽已啟動")

    # 輪詢檢測是否有新的 Challenge 需要發送
    while True:
        try:
            # 若 MQTT 斷線則嘗試重連
            if not bridge_connected:
                connect_with_retry(client)

            if os.path.exists(IN_FILE):
                with open(IN_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)

                cmd_time = data.get("timestamp", 0)
                if cmd_time > last_challenge_time:
                    print("\n📤 [Bridge] 偵測到新的 Challenge 任務，準備發送...")
                    payload_to_send = json.dumps(
                        {
                            "challenge": data.get("challenge"),
                            "noise_level": data.get("noise_level", 3),
                            "timestamp": cmd_time,
                        }
                    )

                    result = client.publish(TOPIC_CHALLENGE, payload_to_send, qos=1)
                    if result.rc == mqtt.MQTT_ERR_SUCCESS:
                        print("✅ [Bridge] Challenge 已透過 MQTT 成功發送")
                        last_challenge_time = cmd_time

                        # 清空目前的 response_in.json，等待新回應
                        with open(OUT_FILE, "w", encoding="utf-8") as rf:
                            json.dump({}, rf)

                        write_heartbeat("challenge forwarded")
                    else:
                        print(f"❌ [Bridge] 發送 Challenge 失敗，代碼: {result.rc}")
                        write_heartbeat(f"publish failed: {result.rc}")

        except json.JSONDecodeError:
            # 檔案正在寫入中，下一輪再讀
            pass
        except Exception as e:
            print(f"❌ [Bridge] 輪詢迴圈錯誤: {e}")
            write_heartbeat(f"loop error: {e}")

        write_heartbeat("running")
        time.sleep(POLL_INTERVAL_SECONDS)

except KeyboardInterrupt:
    print("\n⏹️ 停止 MQTT Bridge...")
finally:
    try:
        client.loop_stop()
        client.disconnect()
    except Exception:
        pass
    print("✅ [Bridge] 已結束")
