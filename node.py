"""
═══════════════════════════════════════════════════════════════════
IoT 硬體指紋認證系統 - MQTT 設備節點 (Node)
═══════════════════════════════════════════════════════════════════

設備節點的核心職責：
1. 訂閱伺服器發送的 Challenge
2. 模擬 PUF (Physically Unclonable Function) 對 Challenge 進行特徵提取
3. 注入硬體製程雜訊（軟體模擬）
4. 透過 MQTT 回傳 Response 給伺服器

系統架構中的角色：
    [Server: VRF Challenge]
              ↓ (MQTT: fujen/iot/challenge)
    [Node: Receive & Process Challenge]
              ↓ (PUF Simulation + Noise Injection)
    [Node: Generate Response]
              ↓ (MQTT: fujen/iot/response)
    [Server: Verify via Hamming Distance]

資料流：
  Challenge (C) 
    → [注入雜訊模擬 PUF] 
    → Response (R, with noise)
    → Hamming Distance = 漢明距離 ≤ Threshold = 認證通過

作者: IoT Security Project  
日期: 2026.03.27
"""

import paho.mqtt.client as mqtt
import json
import random
import time

# ═══════════════════════════════════════════════════════════════
# 【核心函數】PUF 模擬與雜訊注入
# ═══════════════════════════════════════════════════════════════

def simulate_puf_response(challenge_hex, noise_level=3):
    """
    模擬物理上不可複製函數 (PUF) 的運作
    
    背景知識：
      - PUF 是利用晶片製造過程中的隨機變異產生的唯一特徵
      - 每次讀取同一個 Challenge 時，PUF 會產生略微不同的結果（時間變異性）
      - 這種微小的變異就是硬體「雜訊」，也是容錯機制存在的原因
    
    此函數的模擬邏輯：
      1. 收到 Challenge（原始無雜訊的特徵值）
      2. 隨機翻轉若干位元（num_bits），模擬硬體製程的隨機變異
      3. 返回帶有「雜訊」的 Response
    
    參數:
      challenge_hex: 伺服器發送的 Challenge (Hex 字串, 256 bits)
      noise_level: 要翻轉的位元數 (模擬的雜訊強度)
    
    返回:
      response_with_noise: 包含雜訊的 Response (Hex 字串)
      
    例子:
      Challenge (無雜訊): 0xabcd1234...
      Response (加雜訊):  0xabcd1274... (其中幾個位元被隨機翻轉)
    """
    # 轉換 Hex 字串為 256 位的二進制列表
    bits = list(bin(int(challenge_hex, 16))[2:].zfill(256))
    
    # 【重點】隨機選擇 noise_level 個位置進行位元翻轉
    # 這模擬了 PUF 的時間變異性 (temporal variation)
    indices = random.sample(range(256), noise_level)
    
    # 翻轉選定的位元
    for i in indices:
        bits[i] = '1' if bits[i] == '0' else '0'
    
    # 轉回 Hex 字串並返回
    response_hex = hex(int("".join(bits), 2))[2:].zfill(64)
    return response_hex


# ═══════════════════════════════════════════════════════════════
# 【MQTT 回調函數與邏輯】
# ═══════════════════════════════════════════════════════════════

def on_message(client, userdata, msg):
    """
    MQTT 回調函數：當伺服器發送 Challenge 時自動觸發
    
    【資料流 - Step 1】
    伺服器透過 MQTT 發布 Challenge 到 "fujen/iot/challenge" 主題
    此函數捕獲並處理
    
    當收到訊息時執行以下步驟：
    """
    try:
        # Step 1: 解析 MQTT 訊息（JSON 格式）
        # 【資料流說明】伺服器端發送的 JSON 包含 Challenge 和其他元資料
        payload = json.loads(msg.payload.decode('utf-8'))
        challenge = payload.get('challenge')
        
        if not challenge:
            print("❌ [Node] 收到的訊息中缺少 Challenge 欄位")
            return
        
        print(f"\n{'='*60}")
        print(f"📥 [Node] 已接收伺服器的 Challenge")
        print(f"   Challenge 內容: {challenge[:20]}... (截斷顯示)")
        
        # Step 2: 模擬硬體延遲
        # 真實設備會有處理時間，這裡模擬 0.5 秒延遲
        time.sleep(0.5)
        
        # Step 3: 【重點】模擬 PUF 對 Challenge 進行特徵提取
        # 加入雜訊（預設為 3 bits，可由伺服器動態設定）
        # 【資料流說明】Node 將 Challenge 送入虛擬 PUF，產生帶雜訊的 Response
        noise_level = payload.get('noise_level', 3)
        response = simulate_puf_response(challenge, noise_level)
        
        print(f"   PUF 模擬: 注入 {noise_level} bits 雜訊")
        print(f"   Response 內容: {response[:20]}... (截斷顯示)")
        
        # Step 4: 打包 Response 及設備資訊
        # 【資料流說明】將計算完的 Response 加上設備身份，打包為 JSON
        result = {
            "device_id": "FU_JEN_NODE_01",  # 設備唯一標識
            "response": response,             # PUF 產生的響應
            "timestamp": time.time(),         # 時間戳記
            "noise_level": noise_level        # 紀錄所用的雜訊等級
        }
        
        # Step 5: 透過 MQTT 回傳 Response 給伺服器
        # 【資料流說明】發布到 "fujen/iot/response" 主題，伺服器監聽此主題
        client.publish("fujen/iot/response", json.dumps(result))
        
        print(f"📤 [Node] 已回傳 Response 至伺服器")
        print(f"{'='*60}\n")
        
    except json.JSONDecodeError:
        print("❌ [Node] 無法解析 MQTT 傳來的 JSON 資料")
    except Exception as e:
        print(f"❌ [Node] 處理訊息時發生錯誤: {e}")


# ═══════════════════════════════════════════════════════════════
# 【MQTT 客戶端初始化與主迴圈】
# ═══════════════════════════════════════════════════════════════

def main():
    """
    Node 端的主程式：
    1. 初始化 MQTT 客戶端
    2. 連線至 MQTT Broker
    3. 訂閱伺服器的 Challenge 主題
    4. 進入無限迴圈，持續監聽並回應
    """
    
    # 初始化 MQTT 客戶端
    client = mqtt.Client(client_id="IoT_Device_Node_001")
    
    # 設定回調函數
    client.on_message = on_message
    
    print("🚀 [Node] 啟動中...\n")
    print("🔌 正在連線至 MQTT Broker (broker.emqx.io:1883)...")
    
    try:
        # 連線至公開的 MQTT Broker
        client.connect("broker.emqx.io", 1883, 60)
        print("✅ [Node] 已成功連線至 MQTT Broker\n")
        
        # 訂閱伺服器發送 Challenge 的主題
        client.subscribe("fujen/iot/challenge")
        print("📡 [Node] 已訂閱 'fujen/iot/challenge' 主題")
        print("⏳ [Node] 等待伺服器發送挑戰...\n")
        
        print("="*60)
        print("  Node 設備已就位！")
        print("  請在伺服器端 (app.py) 點擊『發送 Challenge』")
        print("="*60 + "\n")
        
        # 進入無限迴圈，持續監聽 MQTT 訊息
        # loop_forever() 會阻塞此執行緒，持續執行直到程式被終止
        client.loop_forever()
        
    except ConnectionRefusedError:
        print("❌ [Node] 無法連線至 Broker，請檢查網路連線")
    except Exception as e:
        print(f"❌ [Node] 發生錯誤: {e}")
    finally:
        print("\n[Node] 正在關閉連線...")
        client.disconnect()
        print("[Node] 已斷開連線")


# ═══════════════════════════════════════════════════════════════
# 程式進入點
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    main()