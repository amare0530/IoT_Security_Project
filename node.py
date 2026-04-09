"""
═══════════════════════════════════════════════════════════════════
IoT 硬體指紋認證系統 - MQTT 設備節點 (Node)
增強版本 - 完善異常處理 & 穩定性改進
═══════════════════════════════════════════════════════════════════

改進項目：
   完善的異常處理
   連接重試機制
   詳細的日誌記錄
   PUF 模擬優化
   線程安全性改進

作者: IoT Security Project
日期: 2026.03.29 (Enhanced)
"""

import paho.mqtt.client as mqtt
import json
import random
import socket
import time
import sys
import traceback
import sqlite3
import os
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
INSTANCE_LOCK_PORT = 45832
DB_PATH = "authentication_history.db"

# Node 回應模式：simulated 或 dataset（預設使用真實資料集）
PUF_MODE = os.getenv("PUF_MODE", "dataset").strip().lower()
DATASET_NAME = os.getenv("DATASET_NAME", "").strip() or None
ALLOW_SIM_FALLBACK = os.getenv("ALLOW_SIM_FALLBACK", "0").strip() == "1"

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
            raise ValueError(f"Noise Level 必須在 0-256 之間，收到: {noise_level}")
        
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
        print(f" [PUF] 驗證錯誤: {str(e)}")
        return None


def normalize_hex(value: str) -> str:
    normalized = (value or "").strip().lower()
    if normalized.startswith("0x"):
        normalized = normalized[2:]
    return normalized


def get_dataset_response(
    challenge_hex: str,
    dataset_name: Optional[str] = None,
    target_device_id: Optional[str] = None,
    target_session_id: Optional[str] = None,
    target_timestamp: Optional[str] = None,
):
    """從 crp_records 取回對應 challenge 的 response 與 metadata。"""
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        normalized_challenge = normalize_hex(challenge_hex)
        query = """
            SELECT device_id, response, source, dataset_name, session_id, temperature_c, supply_proxy
            FROM crp_records
            WHERE challenge = ? AND source = 'real'
        """
        params = [normalized_challenge]

        if dataset_name:
            query += " AND dataset_name = ?"
            params.append(dataset_name)

        if target_device_id:
            query += " AND device_id = ?"
            params.append(target_device_id)

        if target_session_id:
            query += " AND session_id = ?"
            params.append(target_session_id)

        if target_timestamp:
            query += " AND timestamp = ?"
            params.append(target_timestamp)

        query += " ORDER BY RANDOM() LIMIT 1"
        row = cursor.execute(query, params).fetchone()
        conn.close()

        return dict(row) if row else None
    except Exception as e:
        print(f" [Node] 讀取 crp_records 失敗: {e}")
        return None
    except Exception as e:
        print(f" [PUF] 未預期的錯誤: {str(e)}")
        print(traceback.format_exc())
        return None

# ═══════════════════════════════════════════════════════════════
# 【MQTT 回調函數】
# ═══════════════════════════════════════════════════════════════

def on_connect(client, userdata, flags, rc):
    """MQTT 連接回調"""
    if rc == 0:
        print(f" [MQTT] 已連接至 {BROKER_HOST}:{BROKER_PORT}")
        print(f" [MQTT] 訂閱主題: {CHALLENGE_TOPIC}")
        client.subscribe(CHALLENGE_TOPIC)
    else:
        print(f" [MQTT] 連接失敗 (代碼: {rc})")
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
        print(f" [MQTT] 非正常斷開 (代碼: {rc})")
    else:
        print(f"[MQTT] 已正常斷開連接")

def on_message(client, userdata, msg):
    """MQTT 訊息回調 - 核心認證處理邏輯"""
    try:
        print(f"\n{'='*60}")
        print(f" [Node] 已接收伺服器訊息")
        print(f"   主題: {msg.topic}")
        print(f"   QoS: {msg.qos}")
        
        # Step 1: 解析 JSON 訊息
        try:
            payload = json.loads(msg.payload.decode('utf-8'))
        except json.JSONDecodeError as e:
            print(f" [Node] JSON 解析失敗: {str(e)}")
            print(f"   收到的數據: {msg.payload[:100]}")
            return
        except Exception as e:
            print(f" [Node] 解碼錯誤: {str(e)}")
            return
        
        # Step 2: 驗證必要欄位
        challenge = payload.get('challenge')
        nonce = payload.get('nonce')
        challenge_source = payload.get('challenge_source', 'vrf')
        if not challenge:
            print(f" [Node] 缺少 Challenge 欄位")
            return
        
        print(f"   Challenge: {challenge[:20]}... (截斷顯示)")
        print(f"   Challenge Source: {challenge_source}")
        
        # 【Phase 1 新增】Step 2.5: 驗證 Seed 時效性 (防重放)
        timestamp_from_server = payload.get('timestamp')
        if timestamp_from_server:
            time_now = time.time()
            delta_t = time_now - timestamp_from_server
            max_response_time = payload.get('max_response_time', 10)
            
            print(f" [Seed] Challenge 延遲: {delta_t:.2f}s (允許上限: {max_response_time}s)")
            
            if delta_t > max_response_time:
                print(f" [Seed] Challenge 已過期 (超過 {max_response_time}s)")
                print(f"   🚨 拒絕此 Challenge 以防止重放攻擊")
                print(f"{'='*60}\n")
                return
            
            print(f" [Seed] 時效性驗證通過")
        
        # Step 3: 模擬硬體延遲
        delay = 0.5
        print(f" [PUF] 模擬硬體處理 ({delay}s)...")
        time.sleep(delay)
        
        # Step 4: 提取雜訊等級
        noise_level = payload.get('noise_level', 3)
        print(f"🔊 [PUF] 雜訊等級: {noise_level} bits")
        
        response = None
        response_device_id = DEVICE_ID
        response_source = "simulated"
        response_dataset_name = None
        response_session_id = None
        response_temperature_c = None
        response_supply_proxy = None

        # Step 5: 依模式產生回應
        if PUF_MODE == "dataset":
            payload_dataset_name = payload.get("dataset_name")
            target_dataset = payload_dataset_name or DATASET_NAME
            target_device_id = payload.get("target_device_id")
            target_session_id = payload.get("target_session_id")
            target_timestamp = payload.get("target_timestamp")
            record = get_dataset_response(
                challenge,
                dataset_name=target_dataset,
                target_device_id=target_device_id,
                target_session_id=target_session_id,
                target_timestamp=target_timestamp,
            )

            if record:
                response = normalize_hex(record.get("response"))
                response_device_id = record.get("device_id") or DEVICE_ID
                response_source = record.get("source") or "real"
                response_dataset_name = record.get("dataset_name")
                response_session_id = record.get("session_id")
                response_temperature_c = record.get("temperature_c")
                response_supply_proxy = record.get("supply_proxy")
                print(" [Node] 已使用資料集回應模式")
            elif not ALLOW_SIM_FALLBACK:
                print(" [Node] 找不到對應 challenge 的資料集回應，且已停用模擬回退")
                return
            else:
                print(" [Node] 找不到對應資料，回退為模擬模式")

        if response is None:
            response = simulate_puf_response(challenge, noise_level)

        if response is None:
            print(f" [Node] 回應生成失敗")
            return
        
        print(f" [PUF] Response: {response[:20]}... (截斷顯示)")
        
        # Step 6: 準備回傳訊息
        result = {
            "device_id": response_device_id,
            "response": response,
            "timestamp": time.time(),
            "noise_level": noise_level,
            "nonce": nonce,
            "status": "success",
            "source": response_source,
            "dataset_name": response_dataset_name,
            "session_id": response_session_id,
            "temperature_c": response_temperature_c,
            "supply_proxy": response_supply_proxy,
        }
        
        # Step 7: 透過 MQTT 回傳
        try:
            client.publish(RESPONSE_TOPIC, json.dumps(result), qos=1)
            print(f" [Node] 已回傳 Response 至伺服器")
            print(f"   主題: {RESPONSE_TOPIC}")
            print(f"{'='*60}\n")
        except Exception as e:
            print(f" [Node] 回傳失敗: {str(e)}")
    
    except Exception as e:
        print(f" [Node] 未預期的錯誤: {str(e)}")
        print(traceback.format_exc())

# ═══════════════════════════════════════════════════════════════
# 【主程式】
# ═══════════════════════════════════════════════════════════════

def main():
    """Node 主程式"""
    print(" IoT 硬體指紋認證系統 - Node 端")
    print("="*60)
    print(f"設備 ID: {DEVICE_ID}")
    print(f"Broker: {BROKER_HOST}:{BROKER_PORT}")
    print(f"Challenge 主題: {CHALLENGE_TOPIC}")
    print(f"Response 主題: {RESPONSE_TOPIC}")
    print(f"PUF 模式: {PUF_MODE}")
    if PUF_MODE == "dataset":
        print(f"資料集名稱: {DATASET_NAME or '未指定（依 challenge 查詢）'}")
        print(f"模擬回退: {'啟用' if ALLOW_SIM_FALLBACK else '停用'}")
    print("="*60 + "\n")
    
    # 初始化 MQTT 客戶端
    client = None
    retry_count = 0
    lock_socket = None
    
    try:
        # 防止重複啟動多個 node.py 造成回應混淆
        lock_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            lock_socket.bind(("127.0.0.1", INSTANCE_LOCK_PORT))
            lock_socket.listen(1)
        except OSError:
            print(" [Node] 偵測到另一個 node.py 已在執行，請先關閉重複實例")
            sys.exit(1)

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
                print(f" 正在連線至 Broker (嘗試 {retry_count + 1}/{MAX_RETRIES})...")
                
                # 設置連接參數
                client.connect(
                    BROKER_HOST,
                    BROKER_PORT,
                    keepalive=KEEPALIVE
                )
                
                print("="*60)
                print("   Node 設備已就位！")
                print("   等待伺服器發送挑戰...")
                print("="*60 + "\n")
                
                # 進入監聽迴圈
                client.loop_forever()
                break  # 若正常退出则跳出重試迴圈
            
            except ConnectionRefusedError:
                retry_count += 1
                print(f" 連接被拒絕 (嘗試 {retry_count}/{MAX_RETRIES})")
                if retry_count < MAX_RETRIES:
                    print(f" {RETRY_DELAY} 秒後重試...\n")
                    time.sleep(RETRY_DELAY)
            
            except Exception as e:
                retry_count += 1
                print(f" 連接失敗: {str(e)} (嘗試 {retry_count}/{MAX_RETRIES})")
                if retry_count < MAX_RETRIES:
                    print(f" {RETRY_DELAY} 秒後重試...\n")
                    time.sleep(RETRY_DELAY)
        
        # 如果所有重試都失敗
        if retry_count >= MAX_RETRIES:
            print(f"\n 無法連線至 Broker，已嘗試 {MAX_RETRIES} 次")
            print("   請檢查：")
            print("   1. 網路連線是否正常")
            print("   2. Broker 地址是否正確")
            print("   3. 防火牆是否阻擋 1883 連接埠")
            sys.exit(1)
    
    except KeyboardInterrupt:
        print("\n\n [Node] 使用者中斷連接")
    
    except Exception as e:
        print(f"\n [Node] 發生嚴重錯誤: {str(e)}")
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
                print(f" [Node] 清理過程中出錯: {str(e)}")
        if lock_socket:
            try:
                lock_socket.close()
            except Exception:
                pass

# ═══════════════════════════════════════════════════════════════
# 程式進入點
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    main()



