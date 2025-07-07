# 使用指南

本页面提供 Hajimi 的详细使用说明，帮助您充分利用所有功能。

## 🎯 基本使用

### Web 管理界面

部署完成后，访问您的服务地址即可进入 Web 管理界面：

```
http://your-domain:7860
```

使用配置的密码登录后，您可以：
- 📊 查看实时统计数据
- ⚙️ 修改配置参数
- 📈 监控 API 使用情况
- 📝 查看系统日志

### API 调用

Hajimi 提供兼容 OpenAI 格式的 API 接口：

```bash
curl -X POST http://your-domain:7860/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your_password" \
  -d '{
    "model": "gemini-pro",
    "messages": [
      {"role": "user", "content": "你好，Hajimi！"}
    ]
  }'
```

---

## 🔧 客户端接入

### SillyTavern 配置

1. **打开 API 设置**
   - 点击插头图标打开 API 连接设置

2. **选择 API 类型**
   - API: 选择 **聊天补全**
   - 聊天补全来源: 选择 **自定义（兼容 OpenAI）**

3. **填写连接信息**
   - 自定义端点（基础 URL）: `http://your-domain:7860/v1`
   - 自定义 API 密钥: 您的访问密码

4. **启用流式传输**
   - 建议开启流式传输选项以获得更好体验

### 其他客户端

Hajimi 兼容 OpenAI API 格式，支持以下客户端：
- **ChatGPT-Next-Web**
- **Chatbot UI** 
- **Open WebUI**
- **LibreChat**
- **LobeChat**

配置方法类似，使用 `http://your-domain:7860/v1` 作为 API 端点。

---

## ⚙️ 功能特性

### 假流式传输

解决客户端连接超时问题：

```bash
FAKE_STREAMING=true
```

当启用后，Hajimi 会在等待响应期间发送保持连接的空包，避免客户端断开连接。

### 并发请求控制

智能管理并发请求：

```bash
CONCURRENT_REQUESTS=1           # 默认并发数
MAX_CONCURRENT_REQUESTS=3       # 最大并发数
INCREASE_CONCURRENT_ON_FAILURE=1 # 失败时增加并发
```

### 智能重试机制

自动处理请求失败：

```bash
MAX_EMPTY_RESPONSES=5  # 空响应重试次数
```

### 随机字符串伪装

避免请求被检测：

```bash
RANDOM_STRING=true      # 启用伪装
RANDOM_STRING_LENGTH=5  # 伪装字符串长度
```

### 联网搜索模式

让 AI 具备联网搜索能力：

```bash
SEARCH_MODE=true
SEARCH_PROMPT=使用搜索工具联网搜索，需要在content中结合搜索内容
```

---

## 📊 监控与统计

### 实时数据

Web 界面提供丰富的实时监控数据：

- **API 密钥统计**: 每个密钥的使用情况
- **请求统计**: 24小时/每小时/每分钟请求数
- **模型使用**: 各模型的调用频率
- **错误统计**: 请求成功率和错误类型

### 系统日志

查看详细的系统运行日志：
- API 调用记录
- 错误信息
- 性能数据
- 安全事件

---

## 🔐 安全与限制

### 访问控制

```bash
PASSWORD=your_secure_password    # 访问密码
WEB_PASSWORD=admin_password      # Web 界面管理密码
```

### 速率限制

```bash
MAX_REQUESTS_PER_MINUTE=30       # 每分钟请求限制
MAX_REQUESTS_PER_DAY_PER_IP=600  # 每IP每日限制
API_KEY_DAILY_LIMIT=100          # 每密钥每日限制
```

### 白名单模式

```bash
WHITELIST_MODELS=gemini-pro,gemini-pro-vision  # 允许的模型
WHITELIST_USER_AGENT=SillyTavern               # 允许的客户端
```

### 屏蔽列表

```bash
BLOCKED_MODELS=gemini-2.5-pro-preview  # 屏蔽的模型
```

---

## 🚀 高级功能

### Vertex AI 集成

获得更高配额和企业级稳定性：

```bash
ENABLE_VERTEX=true
GOOGLE_CREDENTIALS_JSON='{"type": "service_account"...}'
```

[配置 Vertex AI →](../deploy/vertex.md)

### 缓存优化

```bash
PRECISE_CACHE=false  # 快速缓存模式（推荐）
PRECISE_CACHE=true   # 精确缓存模式
```

### 数据持久化

```bash
ENABLE_STORAGE=true
STORAGE_DIR=/hajimi/settings/
```

---

## 💡 使用技巧

### 优化性能

1. **合理设置并发数**
   ```bash
   CONCURRENT_REQUESTS=3
   MAX_CONCURRENT_REQUESTS=10
   ```

2. **启用缓存**
   ```bash
   PRECISE_CACHE=false
   ```

3. **使用多个 API 密钥**
   ```bash
   GEMINI_API_KEYS=key1,key2,key3,key4
   ```

### 节省配额

1. **设置合理限制**
   ```bash
   API_KEY_DAILY_LIMIT=50
   MAX_REQUESTS_PER_DAY_PER_IP=300
   ```

2. **使用白名单**
   ```bash
   WHITELIST_USER_AGENT=SillyTavern
   ```

### 提高稳定性

1. **启用假流式传输**
   ```bash
   FAKE_STREAMING=true
   ```

2. **设置重试次数**
   ```bash
   MAX_EMPTY_RESPONSES=5
   ```

3. **使用负载均衡**
   - 部署多个实例
   - 使用反向代理分发请求

---

## 🔄 维护操作

### 查看服务状态

```bash
# Docker 部署
docker compose logs hajimi-app

# 直接部署
journalctl -u hajimi -f
```

### 更新服务

```bash
# Docker 部署
docker compose pull
docker compose up -d

# 直接部署
git pull
pip install -r requirements.txt
systemctl restart hajimi
```

### 备份配置

```bash
# 备份环境变量
cp .env .env.backup

# 备份数据目录
tar -czf hajimi-data-$(date +%Y%m%d).tar.gz settings/
```

---

## 📱 移动端使用

### 响应式界面

Hajimi 的 Web 界面完全响应式，在移动设备上也能正常使用：

- 触摸友好的交互
- 适配小屏幕的布局
- 简化的移动端导航

### 移动端客户端

推荐的移动端 AI 客户端：
- **SillyTavern** (WebApp)
- **ChatGPT App** (配置自定义 API)
- **Poe** (通过代理接入)

---

## 🆘 获取帮助

如果使用过程中遇到问题：

1. 查看 [故障排除指南](./troubleshooting.md)
2. 检查 [配置说明](./configuration.md)
3. 搜索 [GitHub Issues](https://github.com/wyeeeee/hajimi/issues)
4. 提交新的问题反馈

---

::: tip 温馨提示
- 定期检查 API 密钥的使用情况，避免超出配额
- 建议设置适当的访问限制，防止滥用
- 保持服务更新到最新版本以获得最佳体验
:::

开始探索 Hajimi 的强大功能吧！