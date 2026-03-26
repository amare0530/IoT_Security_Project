import streamlit as st
import hashlib
import hmac
import random

# 必須放在最前面！設定網頁標題與圖示
st.set_page_config(page_title="IoT 安全驗證系統", page_icon="🔒", layout="centered")

# --- 核心邏輯函數 ---
def calculate_hamming_distance(s1, s2):
    """計算兩個 Hex 字串之間的位元差異數"""
    hex1 = bin(int(s1, 16))[2:].zfill(256)
    hex2 = bin(int(s2, 16))[2:].zfill(256)
    return sum(c1 != c2 for c1, c2 in zip(hex1, hex2))

def inject_noise(hex_str, num_bits):
    """模擬硬體物理雜訊，隨機翻轉指定數量的 Bit"""
    if num_bits == 0:
        return hex_str
    bits = list(bin(int(hex_str, 16))[2:].zfill(256))
    indices = random.sample(range(256), num_bits)
    for i in indices:
        bits[i] = '1' if bits[i] == '0' else '0'
    return hex(int("".join(bits), 2))[2:].zfill(64)

def generate_vrf_challenge(private_key, seed):
    """產生 VRF 挑戰碼與證明"""
    c = hmac.new(private_key.encode(), seed.encode(), hashlib.sha256).hexdigest()
    proof = hashlib.sha256((c + private_key).encode()).hexdigest()[:20]
    return c, proof

# --- 狀態管理 (Session State) ---
# 用來記住產生的 Challenge，避免拉動拉桿時資料消失
if "current_challenge" not in st.session_state:
    st.session_state.current_challenge = None

# --- 主畫面介面 ---
st.title("🔒 IoT 設備驗證伺服器 (Server)")
st.subheader("基於 VRF 的隨機挑戰產生器")

# 側邊欄：設定參數
with st.sidebar:
    st.header("系統設定")
    sk = st.text_input("伺服器私鑰 (SK)", value="FU_JEN_CSIE_SECRET_2026", type="password")
    seed_input = st.text_input("CRP 抽考種子 (Seed)", value="CRP_INDEX_001")

# 產生挑戰區塊
if st.button("🚀 產生隨機挑戰 (Generate Challenge)"):
    c_code, proof_val = generate_vrf_challenge(sk, seed_input)
    # 把結果存進 session_state，讓它跨越網頁重整
    st.session_state.current_challenge = c_code
    
    st.success("成功產出隨機挑戰碼！")
    
    col1, col2 = st.columns(2)
    with col1:
        st.metric(label="挑戰碼 (Challenge C)", value=c_code[:10] + "...")
        st.code(c_code, language="text")
    with col2:
        st.metric(label="驗證證明 (Proof)", value=proof_val)
        st.code(proof_val, language="text")

    st.info("💡 此 C 將透過 MQTT 發送至 Node 端進行 PUF 比對。")

# --- 硬體容錯測試區 (依賴 Session State) ---
st.divider()
st.subheader("🛡️ IoT 硬體容錯測試 (雜訊處理)")

# 確保已經產生過 Challenge 才能進行測試
if st.session_state.current_challenge:
    original_c = st.session_state.current_challenge
    
    noise_level = st.slider("🔧 調整硬體雜訊模擬 (Bit flips)", 0, 10, 0)
    threshold = st.number_input("⚙️ 設定容錯門檻 (Threshold)", value=5, min_value=0, max_value=256)
    
    # 產生帶雜訊的 Response
    noisy_response = inject_noise(original_c, noise_level)
    dist = calculate_hamming_distance(original_c, noisy_response)
    
    st.write(f"📢 模擬硬體回傳特徵: `{noisy_response[:20]}...`")
    st.metric(label="當前漢明距離 (Bit 差異數)", value=dist)
    
    if dist <= threshold:
        st.success(f"✅ 認證成功：硬體特徵符合！(距離 {dist} 在容錯範圍 {threshold} 內)")
    else:
        st.error(f"❌ 認證失敗：雜訊過高或設備偽造！(距離 {dist} 超過門檻 {threshold})")
else:
    st.warning("請先點擊上方按鈕產生隨機挑戰，以進行容錯測試。")

# --- 模擬驗證區 ---
st.divider()
st.subheader("✅ 模擬精確驗證比對 (無容錯)")
test_c = st.text_input("輸入收到的 Challenge C 進行嚴格驗證")
if test_c:
    expect_c, _ = generate_vrf_challenge(sk, seed_input)
    if test_c == expect_c:
        st.balloons()
        st.success("驗證通過：此 Challenge 是由本伺服器合法發出！")
    else:
        st.error("驗證失敗：此資料可能遭到竄改或偽造！")