import paho.mqtt.client as mqtt
import json
import time
import os

BROKER = "broker.emqx.io"
PORT = 1883
TOPIC_CHALLENGE = "fujen/iot/challenge"
TOPIC_RESPONSE = "fujen/iot/response"

OUT_FILE = "response_in.json"
IN_FILE = "challenge_out.json"

last_challenge_time = 0

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print(f"✅ [Bridge] 已成功連接到 MQTT Broker ({BROKER})")
        client.subscribe(TOPIC_RESPONSE, qos=1)
        print(f"✅ [Bridge] 已訂閱主題: {TOPIC_RESPONSE}")
    else:
        print(f"❌ [Bridge] 連接失敗，代碼: {rc}")

def on_message(client, userdata, msg):
    print(f"📥 [Bridge] 收到 MQTT 訊息 (Topic: {msg.topic})")
    try:
        payload = json.loads(msg.payload.decode('utf-8'))
        print(f"   Payload: {str(payload)[:100]}...")
        
        # 寫入檔案供 Streamlit 讀取
        with open(OUT_FILE, "w", encoding="utf-8") as f:
            json.dump({
                "response": payload,
                "received_time": time.time()
            }, f, ensure_ascii=False, indent=2)
            
        print("✅ [Bridge] 已將 Response 寫入", OUT_FILE)
    except Exception as e:
        print(f"❌ [Bridge] 處理訊息錯誤: {e}")

client = mqtt.Client(client_id=f"IoT_Bridge_{int(time.time())}")
client.on_connect = on_connect
client.on_message = on_message

print("啟動 MQTT Bridge 服務中...")
try:
    client.connect(BROKER, PORT, 60)
    client.loop_start()  # 在背景運行 MQTT 監聽
    print("✅ MQTT 背景監聽已啟動")

    # 建立空的 response 檔案 (如果不存在)
    if not os.path.exists(OUT_FILE):
        with open(OUT_FILE, "w") as f:
            json.dump({}, f)
            
    if not os.path.exists(IN_FILE):
        with open(IN_FILE, "w") as f:
            json.dump({}, f)

    # 輪詢檢測是否有新的 Challenge 需要發送
    while True:
        try:
            if os.path.exists(IN_FILE):
                with open(IN_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    
                cmd_time = data.get("timestamp", 0)
                if cmd_time > last_challenge_time:
                    # 有新的 challenge 要發送
                    print(f"\n📤 [Bridge] 偵測到新的 Challenge 任務，準備發送...")
                    payload_to_send = json.dumps({
                        "challenge": data.get("challenge"),
                        "noise_level": data.get("noise_level", 3),
                        "timestamp": cmd_time
                    })
                    
                    result = client.publish(TOPIC_CHALLENGE, payload_to_send, qos=1)
                    if result.rc == mqtt.MQTT_ERR_SUCCESS:
                        print("✅ [Bridge] Challenge 已透過 MQTT 成功發送!")
                        last_challenge_time = cmd_time
                        
                        # 清空目前的 response_in.json (準備等待新的)
                        with open(OUT_FILE, "w", encoding="utf-8") as rf:
                            json.dump({}, rf)
                    else:
                        print(f"❌ [Bridge] 發送挑戰失敗，代碼: {result.rc}")

        except json.JSONDecodeError:
            pass  # 檔案可能正在寫入中，忽略
        except Exception as e:
            print(f"[Bridge loop err] {e}")
            
        time.sleep(0.5)

except KeyboardInterrupt:
    print("\n停止 MQTT Bridge...")
    client.loop_stop()
    client.disconnect()
except Exception as e:
    print(f"發生未預期錯誤: {e}")
