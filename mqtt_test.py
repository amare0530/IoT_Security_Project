#!/usr/bin/env python3
"""
═══════════════════════════════════════════════════════════════════
MQTT 連接診斷工具 - 測試 Server 和 Node 的雙向通信
═══════════════════════════════════════════════════════════════════

用法: python mqtt_test.py

這個腳本將：
1. 連接到 MQTT Broker
2. 構建 Server 監聽器（訂閱 Response）
3. 發送模擬 Challenge
4. 監控是否收到 Response
5. 詳細顯示每一步的診斷信息
"""

import paho.mqtt.client as mqtt
import json
import time
import sys
from datetime import datetime

# 配置
BROKER_HOST = "broker.emqx.io"
BROKER_PORT = 1883
CHALLENGE_TOPIC = "fujen/iot/challenge"
RESPONSE_TOPIC = "fujen/iot/response"

# 狀態跟蹤
test_results = {
    "broker_connection": False,
    "challenge_published": False,
    "response_received": False,
    "challenge_data": None,
    "response_data": None,
    "errors": []
}

def log(level, msg):
    """統一日誌格式"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    icons = {
        "INFO": "ℹ️",
        "SUCCESS": "✅",
        "WARNING": "⚠️",
        "ERROR": "❌",
        "DEBUG": "🐛"
    }
    icon = icons.get(level, "•")
    print(f"{icon} [{timestamp}] {msg}")


class MQTTTestClient:
    """MQTT 測試客戶端"""
    
    def __init__(self):
        self.client = mqtt.Client(client_id=f"MQTT_Test_{int(time.time() * 1000)}")
        self.response_received = False
        self.received_message = None
        
        # 設置回調
        self.client.on_connect = self.on_connect
        self.client.on_disconnect = self.on_disconnect
        self.client.on_message = self.on_message
        self.client.on_subscribe = self.on_subscribe
    
    def on_connect(self, client, userdata, flags, rc):
        """連接回調"""
        if rc == 0:
            log("SUCCESS", f"已連接至 Broker: {BROKER_HOST}:{BROKER_PORT}")
            test_results["broker_connection"] = True
            
            # 訂閱 Response 主題
            log("INFO", f"訂閱主題: {RESPONSE_TOPIC} (QoS=1)")
            client.subscribe(RESPONSE_TOPIC, qos=1)
        else:
            error_msg = f"連接失敗 (代碼: {rc})"
            log("ERROR", error_msg)
            test_results["errors"].append(error_msg)
    
    def on_disconnect(self, client, userdata, rc):
        """斷開回調"""
        if rc != 0:
            log("WARNING", f"非正常斷開 (代碼: {rc})")
        else:
            log("INFO", "正常斷開連線")
    
    def on_subscribe(self, client, userdata, mid, granted_qos):
        """訂閱回調"""
        log("SUCCESS", f"訂閱成功 (Granted QoS: {granted_qos[0]})")
    
    def on_message(self, client, userdata, msg):
        """接收訊息"""
        try:
            log("INFO", f"📥 收到訊息 (主題: {msg.topic}, QoS: {msg.qos})")
            
            payload = json.loads(msg.payload.decode('utf-8'))
            log("SUCCESS", f"Response 已接收！Device ID: {payload.get('device_id')}")
            
            test_results["response_received"] = True
            test_results["response_data"] = payload
            self.response_received = True
            self.received_message = payload
            
            # 詳細顯示 Response
            log("DEBUG", f"Response 內容: {json.dumps(payload, indent=2, ensure_ascii=False)}")
            
        except json.JSONDecodeError as e:
            error_msg = f"JSON 解析失敗: {str(e)}"
            log("ERROR", error_msg)
            test_results["errors"].append(error_msg)
        except Exception as e:
            error_msg = f"處理訊息失敗: {str(e)}"
            log("ERROR", error_msg)
            test_results["errors"].append(error_msg)
    
    def connect(self):
        """連接到 Broker"""
        log("INFO", f"正在連接至 Broker: {BROKER_HOST}:{BROKER_PORT}...")
        try:
            self.client.connect(BROKER_HOST, BROKER_PORT, keepalive=60)
            self.client.loop_start()
            return True
        except Exception as e:
            error_msg = f"連接異常: {str(e)}"
            log("ERROR", error_msg)
            test_results["errors"].append(error_msg)
            return False
    
    def publish_challenge(self, challenge_hex):
        """發送 Challenge"""
        try:
            payload = json.dumps({
                "challenge": challenge_hex,
                "noise_level": 3,
                "timestamp": time.time()
            })
            
            log("INFO", f"向主題 '{CHALLENGE_TOPIC}' 發送 Challenge (QoS=1)...")
            result = self.client.publish(CHALLENGE_TOPIC, payload, qos=1)
            
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                log("SUCCESS", "Challenge 已發送")
                test_results["challenge_published"] = True
                test_results["challenge_data"] = payload
                return True
            else:
                error_msg = f"發送失敗 (返回碼: {result.rc})"
                log("ERROR", error_msg)
                test_results["errors"].append(error_msg)
                return False
        except Exception as e:
            error_msg = f"發送異常: {str(e)}"
            log("ERROR", error_msg)
            test_results["errors"].append(error_msg)
            return False
    
    def wait_for_response(self, timeout=15):
        """等待 Response"""
        log("INFO", f"⏳ 等待 Node Response (超時: {timeout}秒)...")
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            if self.response_received:
                elapsed = time.time() - start_time
                log("SUCCESS", f"Response 已收到 (等待時間: {elapsed:.2f}秒)")
                return True
            
            # 顯示進度
            elapsed = time.time() - start_time
            print(f"\r⏳ 等待中 ({elapsed:.1f}s/{timeout}s)...", end="", flush=True)
            time.sleep(0.5)
        
        print()  # 換行
        error_msg = f"超時 - 未在 {timeout} 秒內收到 Response"
        log("ERROR", error_msg)
        test_results["errors"].append(error_msg)
        return False
    
    def disconnect(self):
        """斷開連線"""
        log("INFO", "正在斷開連線...")
        self.client.loop_stop()
        self.client.disconnect()


def generate_test_challenge():
    """生成測試用 Challenge"""
    import hashlib
    test_data = f"TEST_{int(time.time())}".encode()
    return hashlib.sha256(test_data).hexdigest()


def print_summary():
    """列印測試總結"""
    print("\n" + "="*70)
    print("📊 測試結果總結")
    print("="*70)
    
    result_lines = [
        ("Broker 連接", "✅" if test_results["broker_connection"] else "❌"),
        ("Challenge 已發送", "✅" if test_results["challenge_published"] else "❌"),
        ("Response 已收到", "✅" if test_results["response_received"] else "❌"),
    ]
    
    for label, status in result_lines:
        print(f"{label:.<40} {status}")
    
    if test_results["errors"]:
        print("\n❌ 發生的錯誤：")
        for i, error in enumerate(test_results["errors"], 1):
            print(f"   {i}. {error}")
    
    print("\n" + "="*70)
    
    # 最終判定
    if test_results["response_received"]:
        print("✅ 測試成功！MQTT 雙向通信運作正常。")
        print("可以放心使用 app.py 進行認證測試。\n")
        return 0
    elif test_results["broker_connection"] and test_results["challenge_published"]:
        print("⚠️ 連接和發送成功，但未收到 Response。")
        print("請確保 Node 端正常運行 (python node.py)。\n")
        return 1
    else:
        print("❌ 測試失敗。請檢查：")
        print("1. 網路連線是否正常")
        print("2. Broker 地址是否正確 (broker.emqx.io:1883)")
        print("3. 防火牆是否阻擋連接\n")
        return 2


def main():
    """主測試程式"""
    print("="*70)
    print("🧪 MQTT 連接診斷工具")
    print("="*70)
    print(f"Broker: {BROKER_HOST}:{BROKER_PORT}")
    print(f"Challenge 主題: {CHALLENGE_TOPIC}")
    print(f"Response 主題: {RESPONSE_TOPIC}")
    print("="*70 + "\n")
    
    # 1. 建立客戶端和連接
    client = MQTTTestClient()
    
    if not client.connect():
        log("ERROR", "無法連接至 Broker，終止測試")
        return 2
    
    # 等待連接完成
    time.sleep(1)
    
    if not test_results["broker_connection"]:
        log("ERROR", "Broker 連接失敗，終止測試")
        return 2
    
    # 2. 發送 Challenge
    challenge_hex = generate_test_challenge()
    log("INFO", f"生成測試 Challenge: {challenge_hex[:32]}...")
    
    if not client.publish_challenge(challenge_hex):
        log("ERROR", "Challenge 發送失敗")
        client.disconnect()
        return 2
    
    # 3. 等待 Response
    time.sleep(1)  # 給訊息發送機會
    received = client.wait_for_response(timeout=15)
    
    # 4. 斷開連線
    time.sleep(0.5)
    client.disconnect()
    
    # 5. 列印結果
    exit_code = print_summary()
    
    return exit_code


if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\n⏹️ 測試被使用者中斷")
        sys.exit(1)
    except Exception as e:
        log("ERROR", f"未預期的錯誤: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(3)
