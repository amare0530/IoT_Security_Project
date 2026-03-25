import streamlit as st
import hashlib
import hmac

# --- VRF 邏輯核心 ---
def generate_vrf_challenge(private_key, seed):
    c = hmac.new(private_key.encode(), seed.encode(), hashlib.sha256).hexdigest()
    proof = hashlib.sha256((c + private_key).encode()).hexdigest()[:20]
    return c, proof

# --- Streamlit 網頁介面 ---
st.set_page_config(page_title="IoT 安全驗證系統", page_icon="🔒")

st.title("🔒 IoT 設備驗證伺服器 (Server)")
st.subheader("基於 VRF 的隨機挑戰產生器")

# 側邊欄：設定參數
with st.sidebar:
    st.header("系統設定")
    sk = st.text_input("伺服器私鑰 (SK)", value="FU_JEN_CSIE_SECRET_2026", type="password")
    seed_input = st.text_input("CRP 抽考種子 (Seed)", value="CRP_INDEX_001")

# 主畫面：產生挑戰
if st.button("🚀 產生隨機挑戰 (Generate Challenge)"):
    c_code, proof_val = generate_vrf_challenge(sk, seed_input)
    
    st.success("成功產出隨機挑戰碼！")
    
    col1, col2 = st.columns(2)
    with col1:
        st.metric(label="挑戰碼 (Challenge C)", value=c_code[:10] + "...")
        st.code(c_code, language="text")
    with col2:
        st.metric(label="驗證證明 (Proof)", value=proof_val)
        st.code(proof_val, language="text")

    st.info("💡 此 C 將透過 MQTT 發送至 Node 端進行 PUF 比對。")

# 模擬驗證區
st.divider()
st.subheader("✅ 模擬驗證比對")
test_c = st.text_input("輸入收到的 Challenge C 進行驗證")
if test_c:
    expect_c, _ = generate_vrf_challenge(sk, seed_input)
    if test_c == expect_c:
        st.balloons()
        st.success("驗證通過：此 Challenge 是由本伺服器合法發出！")
    else:
        st.error("驗證失敗：此資料可能遭到竄改或偽造！")