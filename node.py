"""
═══════════════════════════════════════════════════════════════════
IoT 硬體指紋認證系統 - MQTT 設備節點 (Node)
增強版本 - 完善異常處理 & 穩定性改進
═══════════════════════════════════════════════════════════════════

改進項目：
  ✅ 完善的異常處理
  ✅ 連接重試機制
  ✅ 詳細的日誌記錄
  ✅ PUF 模擬優化
  ✅ 線程安全性改進

作者: IoT Security Project
日期: 2026.03.29 (Enhanced)
"""

import paho.mqtt.client as mqtt
import json
import random
import time
import sys
import traceback
from typing import Optional

# ═══════════════════════════════════════════════════════════════
# 【配置常數】
# ═══════════════════════════════════════════════════════════════

BROKER_HOST = "broker.emqx.io"
BROKER_PORT = 1883
CHALLENGE_TOPIC = "fujen/iot/challenge"
RESPONSE_TOPIC = "fujen/iot/response"
DEVICE_ID = "FU_JEN_NODE_01"
KEEPALIVE = 60
MAX_RETRIES = 5
RETRY_DELAY = 3  # 秒

# ═══════════════════════════════════════════════════════════════
# 【PUF 模擬核心函數】
# ═══════════════════════════════════════════════════════════════

def simulate_puf_response(challenge_hex: str, noise_level: int = 3) -> Optional[str]:
    """
    模擬物理上不可複製函數 (PUF) 的運作
    
    參數:
      challenge_hex: 256-bit 十六進位挑戰碼
      noise_level: 要翻轉的位元數 (0-20)
    
    返回:
      帶雜訊的響應 Hex 字串，或 None 如果出錯
    """
    try:
        # 驗證輸入
        if not challenge_hex:
            raise ValueError("Challenge 不能為空")
        
        if not isinstance(noise_level, int) or noise_level < 0 or noise_level > 256:
            raise ValueError(f"Noise Level 必须在 0-256 之間，收到: {noise_level}")
        
        # 轉換 Hex 為二進制
        try:
            bits = list(bin(int(challenge_hex, 16))[2:].zfill(256))
        except ValueError:
            raise ValueError(f"無效的 Hex 字串: {challenge_hex[:20]}...")
        
        if noise_level == 0:
            return challenge_hex
        
        # 隨機選擇要翻轉的位置
        indices = random.sample(range(256), noise_level)
        
        # 翻轉位元
        for i in indices:
            bits[i] = '1' if bits[i] == '0' else '0'
        
        # 轉回 Hex 字串
        response_hex = hex(int("".join(bits), 2))[2:].zfill(64)
        
        return response_hex
    
    except ValueError as e:
        print(f"❌ [PUF] 驗證錯誤: {str(e)}")
        return None
    except Exception as e:
        print(f"❌ [PUF] 未預期的錯誤: {str(e)}")
        print(traceback.format_exc())
        return None

# ═══════════════════════════════════════════════════════════════
# 【MQTT 回調函數】
# ═══════════════════════════════════════════════════════════════

def on_connect(client, userdata, flags, rc):
    """MQTT 連接回調"""
    if rc == 0:
        print(f"✅ [MQTT] 已連接至 {BROKER_HOST}:{BROKER_PORT}")
        print(f"📡 [MQTT] 訂閱主題: {CHALLENGE_TOPIC}")
        client.subscribe(CHALLENGE_TOPIC)
    else:
        print(f"❌ [MQTT] 連接失敗 (代碼: {rc})")
        error_messages = {
            1: "協議版本不支援",
            2: "無效的客戶端識別符",
            3: "伺服器無法使用",
            4: "使用者名稱或密碼有誤",
            5: "沒有授權"
        }
        print(f"   原因: {error_messages.get(rc, '未知錯誤')}")

def on_disconnect(client, userdata, rc):
    """MQTT 斷開連接回調"""
    if rc != 0:
        print(f"⚠️ [MQTT] 非正常斷開 (代碼: {rc})")
    else:
        print(f"[MQTT] 已正常斷開連接")

def on_message(client, userdata, msg):
    """MQTT 訊息回調 - 核心認證處理邏輯"""
    try:
        print(f"\n{'='*60}")
        print(f"📥 [Node] 已接收伺服器訊息")
        print(f"   主題: {msg.topic}")
        print(f"   QoS: {msg.qos}")
        
        # Step 1: 解析 JSON 訊息
        try:
            payload = json.loads(msg.payload.decode('utf-8'))
        except json.JSONDecodeError as e:
            print(f"❌ [Node] JSON 解析失敗: {str(e)}")
            print(f"   收到的數據: {msg.payload[:100]}")
            return
        except Exception as e:
            print(f"❌ [Node] 解碼錯誤: {str(e)}")
            return
        
        # Step 2: 驗證必要欄位
        challenge = payload.get('challenge')
        if not challenge:
            print(f"❌ [Node] 缺少 Challenge 欄位")
            return
        
        print(f"   Challenge: {challenge[:20]}... (截斷顯示)")
        
        # Step 3: 模擬硬體延遲
        delay = 0.5
        print(f"⏳ [PUF] 模擬硬體處理 ({delay}s)...")
        time.sleep(delay)
        
        # Step 4: 提取雜訊等級
        noise_level = payload.get('noise_level', 3)
        print(f"🔊 [PUF] 雜訊等級: {noise_level} bits")
        
        # Step 5: 執行 PUF 模擬
        response = simulate_puf_response(challenge, noise_level)
        
        if response is None:
            print(f"❌ [Node] PUF 模擬失敗")
            return
        
        print(f"📊 [PUF] Response: {response[:20]}... (截斷顯示)")
        
        # Step 6: 準備回傳訊息
        result = {
            "device_id": DEVICE_ID,
            "response": response,
            "timestamp": time.time(),
            "noise_level": noise_level,
            "status": "success"
        }
        
        # Step 7: 透過 MQTT 回傳
        try:
            client.publish(RESPONSE_TOPIC, json.dumps(result), qos=1)
            print(f"📤 [Node] 已回傳 Response 至伺服器")
            print(f"   主題: {RESPONSE_TOPIC}")
            print(f"{'='*60}\n")
        except Exception as e:
            print(f"❌ [Node] 回傳失敗: {str(e)}")
    
    except Exception as e:
        print(f"❌ [Node] 未預期的錯誤: {str(e)}")
        print(traceback.format_exc())

# ═══════════════════════════════════════════════════════════════
# 【主程式】
# ═══════════════════════════════════════════════════════════════

def main():
    """Node 主程式"""
    print("🚀 IoT 硬體指紋認證系統 - Node 端")
    print("="*60)
    print(f"設備 ID: {DEVICE_ID}")
    print(f"Broker: {BROKER_HOST}:{BROKER_PORT}")
    print(f"Challenge 主題: {CHALLENGE_TOPIC}")
    print(f"Response 主題: {RESPONSE_TOPIC}")
    print("="*60 + "\n")
    
    # 初始化 MQTT 客戶端
    client = None
    retry_count = 0
    
    try:
        client = mqtt.Client(
            client_id=f"{DEVICE_ID}_{int(time.time())}",
            clean_session=True
        )
        
        # 設置回調函數
        client.on_connect = on_connect
        client.on_disconnect = on_disconnect
        client.on_message = on_message
        
        # 設置 Will 訊息（如果連接異常斷開）
        client.will_set(
            RESPONSE_TOPIC,
            json.dumps({
                "device_id": DEVICE_ID,
                "status": "offline",
                "timestamp": time.time()
            }),
            qos=1
        )
        
        # 連接迴圈（含重試機制）
        while retry_count < MAX_RETRIES:
            try:
                print(f"🔌 正在連線至 Broker (嘗試 {retry_count + 1}/{MAX_RETRIES})...")
                
                # 設置連接參數
                client.connect(
                    BROKER_HOST,
                    BROKER_PORT,
                    keepalive=KEEPALIVE
                )
                
                print("="*60)
                print("  ✅ Node 設備已就位！")
                print("  ⏳ 等待伺服器發送挑戰...")
                print("="*60 + "\n")
                
                # 進入監聽迴圈
                client.loop_forever()
                break  # 若正常退出则跳出重試迴圈
            
            except ConnectionRefusedError:
                retry_count += 1
                print(f"❌ 連接被拒絕 (嘗試 {retry_count}/{MAX_RETRIES})")
                if retry_count < MAX_RETRIES:
                    print(f"⏳ {RETRY_DELAY} 秒後重試...\n")
                    time.sleep(RETRY_DELAY)
            
            except Exception as e:
                retry_count += 1
                print(f"❌ 連接失敗: {str(e)} (嘗試 {retry_count}/{MAX_RETRIES})")
                if retry_count < MAX_RETRIES:
                    print(f"⏳ {RETRY_DELAY} 秒後重試...\n")
                    time.sleep(RETRY_DELAY)
        
        # 如果所有重試都失敗
        if retry_count >= MAX_RETRIES:
            print(f"\n❌ 無法連線至 Broker，已嘗試 {MAX_RETRIES} 次")
            print("   請檢查：")
            print("   1. 網路連線是否正常")
            print("   2. Broker 地址是否正確")
            print("   3. 防火牆是否阻擋 1883 連接埠")
            sys.exit(1)
    
    except KeyboardInterrupt:
        print("\n\n⏹️ [Node] 使用者中斷連接")
    
    except Exception as e:
        print(f"\n❌ [Node] 發生嚴重錯誤: {str(e)}")
        print(traceback.format_exc())
        sys.exit(1)
    
    finally:
        # 清理連接
        if client:
            try:
                print("\n[Node] 正在關閉連線...")
                client.loop_stop()
                client.disconnect()
                print("[Node] 已斷開連線")
            except Exception as e:
                print(f"⚠️ [Node] 清理過程中出錯: {str(e)}")

# ═══════════════════════════════════════════════════════════════
# 程式進入點
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    main()
