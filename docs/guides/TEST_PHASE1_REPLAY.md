# Phase 1 集成测试指南

## 🎯 测试目标
验证动态种子生成和重放攻击检测是否正常工作

## 📋 测试步骤

### 1️⃣ 启动系统
```bash
# Terminal 1: MQTT Bridge
python mqtt_bridge.py

# Terminal 2: IoT 节点
python node.py

# Terminal 3: Streamlit 服务器
streamlit run app.py
```

### 2️⃣ 测试场景 A - 正常认证流程
1. 在 Streamlit UI 中找到"動態 Challenge"部分
2. **勾选** "使用動態 Seed (防重放)" 复选框
3. 设置时间粒度 = 1 秒，超时 = 10 秒
4. 点击"生成 Challenge"按钮
   - 应该看到: ✅ 動態 Challenge 已生成 (防重放)
   - 应该显示 Nonce 和 Timestamp
5. 点击"發送 Challenge"按钮
   - 应该看到: ✅ Challenge 已發送
6. 点击"驗證最新回應"按钮
   - 应该看到: 认证通过 (pass) 或 (fail，取决于PUF噪声)
   - **重要**: 应该 **有 Nonce 数据** 在结果中

### 3️⃣ 测试场景 B - 重放攻击检测
1. 首先执行测试场景 A（正常认证）
2. **立即再次** 点击"驗證最新回應"按钮
   - 应该看到错误: 🚨 重放攻擊防禦觸發: Nonce 已使用
   - **这证明系统正确拒绝了重复使用**

### 4️⃣ 测试场景 C - 过期 Challenge 拒绝
1. 在 Streamlit UI 中设置 `seed_timeout = 2 秒`
2. 生成 Challenge
3. 等待 **3 秒钟**
4. 点击"發送 Challenge"
   - Node 端应该打印: ❌ Challenge 已過期 (超過 2s)
   - 不应该从 Node 收到 Response
5. Node 日志应该显示: 🚨 拒絕此 Challenge 以防止重放攻擊

### 5️⃣ 测试场景 D - 静态模式（对照组）
1. **取消勾选** "使用動態 Seed" 复选框
2. 生成 Challenge → 发送 → 验证
   - 应该看到: ⚠️ 使用靜態 Seed（未啟用重放攻擊防禦）
   - 系统应该正常工作，但 **没有 Nonce 保护**

---

## ✅ 预期结果

| 场景 | 状态 | 证据 |
|------|------|------|
| A - 正常认证 | ✅ | Challenge 生成 + Nonce 显示 + Response 验证 |
| B - 重放检测 | ✅ | 第二次尝试被拒绝，错误显示 "Nonce 已使用" |
| C - 过期 Challenge | ✅ | Node 拒绝消息 + 无 Response |
| D - 静态模式 | ✅ | 正常工作但无动态保护 |

---

## 🐛 调试信息

查看以下日志文件：
- **app.py** (Streamlit): 查看 Console 窗口输出
- **node.py**: 查看"⏱️ [Seed] Challenge 延遲"和"✅ [Seed] 時效性驗證通過"日志
- **JSON 文件**:
  - `challenge_out.json`: 应该包含 "timestamp" + "nonce" + "max_response_time" 字段
  - `response_in.json`: 应该包含 "timestamp" + "status" 字段

---

## 📊 数据库验证

完成测试后，检查 SQLite 数据库：

```bash
sqlite3 authentication_history.db
SELECT challenge, response, hamming_distance, result FROM auth_history ORDER BY created_at DESC LIMIT 5;
```

应该看到最近的认证记录，其中：
- ✅ 第一条: result = "pass" 或 "fail" (取决于 PUF 噪声)
- ❌ 第二条: result = "fail", 且带有重放攻击错误信息

---

## 🚀 下周任务

- [ ] 通过所有 5 个测试场景
- [ ] 准备演示给老师 (Monday EOD)
- [ ] 记录任何时钟偏差问题
- [ ] 根据老师反馈进行调整
