"""
配置文件 - IoT 硬體指紋認證系統
=================================

集中管理所有系統配置、常數和設定

"""

# ═══════════════════════════════════════════════════════════════
# MQTT 配置
# ═══════════════════════════════════════════════════════════════

MQTT_CONFIG = {
    # Broker 設定
    "broker_host": "broker.emqx.io",      # MQTT Broker 地址
    "broker_port": 1883,                  # MQTT Broker 連接埠
    "connection_timeout": 60,             # 連接超時 (秒)
    
    # 主題設定
    "topic_challenge": "fujen/iot/challenge",   # 伺服器發送 Challenge 的主題
    "topic_response": "fujen/iot/response",     # Node 回傳 Response 的主題
    
    # 客戶端設定
    "server_client_id": "IoT_Server_001",       # 伺服器 MQTT Client ID
    "node_client_id": "IoT_Device_Node_001",    # Node 設備 Client ID
    "keepalive": 60,                            # Keep-alive 間隔 (秒)
}

# 【生產環境建議】
# 若要使用私有 Broker，修改如下：
# MQTT_CONFIG["broker_host"] = "your.mqtt.broker.com"
# 並啟用 TLS 與身份驗證
MQTT_TLS_CONFIG = {
    "ca_certs": None,           # CA 憑證路徑
    "certfile": None,           # 客戶端憑證
    "keyfile": None,            # 客戶端密鑰
    "tls_version": None,        # TLS 版本
    "ciphers": None,            # 加密套件
}

MQTT_AUTH_CONFIG = {
    "username": None,           # 使用者名稱
    "password": None,           # 密碼
}

# ═══════════════════════════════════════════════════════════════
# VRF 與密碼學設定
# ═══════════════════════════════════════════════════════════════

VRF_CONFIG = {
    # VRF 私鑰 (Server Secret Key)
    "server_secret_key": "FU_JEN_CSIE_SECRET_2026",
    
    # 預設 CRP 種子
    "default_seed": "CRP_INDEX_001",
    
    # 密碼學算法
    "hash_algorithm": "sha256",     # 使用的雜湊算法
    "proof_length": 20,            # Proof 的長度 (十六進位字符數)
}

# ═══════════════════════════════════════════════════════════════
# PUF 與硬體模擬設定
# ═══════════════════════════════════════════════════════════════

PUF_CONFIG = {
    # 挑戰與響應的位元長度
    "challenge_bits": 256,          # 挑戰碼位元數
    "response_bits": 256,           # 響應位元數
    "challenge_hex_length": 64,     # 十六進位字符長度 (256 bits / 4)
    
    # PUF 特性設定
    "default_noise_level": 3,       # 預設雜訊等級 (位元翻轉數)
    "max_noise_level": 20,          # 最大雜訊等級
    
    # 容錯設定
    "default_threshold": 5,         # 預設容錯門檻
    "max_threshold": 256,           # 最大容錯門檻
}

# 研究預設：偏保守、貼近真實硬體（非理想 IID 雜訊）
REALISTIC_PUF_PROFILE = {
    "noise_sigma": 0.03,
    "bias_ratio": 0.10,
    "bias_strength": 0.90,
    "unstable_ratio": 0.08,
    "unstable_extra_noise": 0.08,
    "cluster_noise_prob": 0.02,
    "cluster_size": 4,
    "env_noise_sigma": 0.005,
    "env_spike_prob": 0.05,
    "env_spike_min": 0.05,
    "env_spike_max": 0.12,
}

# ═══════════════════════════════════════════════════════════════
# 實驗參數設定
# ═══════════════════════════════════════════════════════════════

EXPERIMENT_CONFIG = {
    # 批量實驗設定
    "batch_size": 100,              # 每次批量實驗的次數
    "experiment_noise_range": [0, 20],      # 雜訊等級測試範圍
    "experiment_threshold_range": [0, 256], # 門檻測試範圍
    
    # FRR/FAR 門檻定義
    "frr_excellent_threshold": 5,   # FRR 優秀的上限 (%)
    "frr_acceptable_threshold": 10, # FRR 可接受的上限 (%)
    
    # 結果匯出設定
    "export_format": "csv",         # 匯出格式
    "export_directory": "./results", # 實驗結果導出目錄
}

# ═══════════════════════════════════════════════════════════════
# UI 與顯示設定
# ═══════════════════════════════════════════════════════════════

UI_CONFIG = {
    # Streamlit 頁面設定
    "page_title": "IoT 安全驗證系統",
    "page_icon": "",
    "layout": "wide",               # 使用寬版式
    
    # 時間相關顯示
    "timestamp_format": "%Y-%m-%d %H:%M:%S",
    
    # 數據顯示精度
    "frr_precision": 2,             # FRR 顯示小數位數
    "distance_precision": 1,        # 距離顯示小數位數
}

# ═══════════════════════════════════════════════════════════════
# 日誌與偵錯設定
# ═══════════════════════════════════════════════════════════════

DEBUG_CONFIG = {
    # 偵錯模式
    "debug_mode": False,            # 啟用詳細日誌輸出
    
    # 日誌等級
    "log_level": "INFO",            # DEBUG, INFO, WARNING, ERROR
    
    # 日誌輸出
    "log_to_file": False,           # 是否輸出到文件
    "log_file": "./logs/iot_auth.log",
}

# ═══════════════════════════════════════════════════════════════
# 安全設定與限制
# ═══════════════════════════════════════════════════════════════

SECURITY_CONFIG = {
    # 速率限制
    "max_challenges_per_minute": 60,    # 每分鐘最多發送的Challenge數
    "max_authentication_attempts": 10,  # 允許的最大認證嘗試次數
    
    # 超時設定
    "challenge_timeout": 60,             # Challenge 有效期 (秒)
    "response_wait_timeout": 30,         # Server 等待 Response 的超時 (秒)
    
    # 安全警告
    "warn_on_high_frr": True,            # FRR > 10% 時發出警告
    "warn_on_low_threshold": True,       # 門檻 < 1 時發出警告
}

# ═══════════════════════════════════════════════════════════════
# 工具函數：動態獲取配置
# ═══════════════════════════════════════════════════════════════

def get_mqtt_config(key=None):
    """
    獲取 MQTT 配置
    
    使用方式：
        config = get_mqtt_config()
        broker = config["broker_host"]
        
    或
        broker = get_mqtt_config("broker_host")
    """
    if key:
        return MQTT_CONFIG.get(key)
    return MQTT_CONFIG

def get_vrf_config(key=None):
    """獲取 VRF 配置"""
    if key:
        return VRF_CONFIG.get(key)
    return VRF_CONFIG

def get_puf_config(key=None):
    """獲取 PUF 配置"""
    if key:
        return PUF_CONFIG.get(key)
    return PUF_CONFIG

def get_realistic_puf_profile(key=None):
    """取得偏保守的現實噪聲配置，用於論文與壓測基線。"""
    if key:
        return REALISTIC_PUF_PROFILE.get(key)
    return REALISTIC_PUF_PROFILE

def validate_noise_level(noise):
    """驗證雜訊等級是否有效"""
    max_noise = PUF_CONFIG["max_noise_level"]
    return 0 <= noise <= max_noise

def validate_threshold(threshold):
    """驗證容錯門檻是否有效"""
    max_threshold = PUF_CONFIG["max_threshold"]
    return 0 <= threshold <= max_threshold

# ═══════════════════════════════════════════════════════════════
# 範例使用
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    # 使用範例
    print(" IoT Security Configuration")
    print("=" * 60)
    
    # 取得 MQTT 配置
    mqtt_cfg = get_mqtt_config()
    print(f"MQTT Broker: {mqtt_cfg['broker_host']}:{mqtt_cfg['broker_port']}")
    print(f"Challenge Topic: {mqtt_cfg['topic_challenge']}")
    print(f"Response Topic: {mqtt_cfg['topic_response']}")
    
    # 取得 VRF 配置
    vrf_cfg = get_vrf_config()
    print(f"\nVRF Server Key: {vrf_cfg['server_secret_key']}")
    
    # 取得 PUF 配置
    puf_cfg = get_puf_config()
    print(f"\nPUF Bits: {puf_cfg['challenge_bits']}")
    print(f"Default Noise Level: {puf_cfg['default_noise_level']}")
    print(f"Default Threshold: {puf_cfg['default_threshold']}")
    
    # 驗證參數
    print(f"\nValidation:")
    print(f"Noise 3 bits valid? {validate_noise_level(3)}")
    print(f"Threshold 5 valid? {validate_threshold(5)}")

