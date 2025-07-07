# 快速开始

Hajimi 支持多种部署方式，您可以根据自己的需求和环境选择最合适的方案。

## 🎯 选择部署方式

### 🐳 Docker 部署
**推荐指数**: ⭐⭐⭐⭐⭐  
**适用场景**: 本地开发、服务器部署、NAS

- ✅ 部署简单，一键启动
- ✅ 配置灵活，支持自定义
- ✅ 更新方便，自动化程度高
- ✅ 跨平台支持

[Docker 部署教程 →](./docker.md)

---

### ☁️ 免费云端部署

#### Hugging Face Spaces
**推荐指数**: ⭐⭐⭐⭐⭐  
**费用**: 完全免费

- ✅ 无需服务器
- ✅ 操作简单
- ✅ 稳定可靠
- ✅ 自动更新

[Hugging Face 部署教程 →](./huggingface.md)

#### Claw Cloud
**推荐指数**: ⭐⭐⭐⭐  
**费用**: 每月 10GB 免费流量

- ✅ GitHub 登录即可使用
- ✅ 配置相对简单
- ✅ 支持自定义域名
- ⚠️ 有流量限制

[Claw Cloud 部署教程 →](./claw.md)

#### Zeabur
**推荐指数**: ⭐⭐⭐⭐  
**费用**: 有免费额度

- ✅ 一键部署
- ✅ 自动扩容
- ✅ 支持自定义域名
- ⚠️ 有使用限制

[Zeabur 部署教程 →](./zeabur.md)

---

### 📱 移动端部署

#### Termux + Ubuntu
**推荐指数**: ⭐⭐⭐  
**适用场景**: Android 设备

- ✅ 本地运行，无需网络
- ✅ 完全免费
- ⚠️ 配置相对复杂
- ⚠️ 性能有限

[Termux 部署教程 →](./termux.md)

---

## ⚡ 5分钟快速部署

### 方案一：Docker（推荐）

```bash
# 1. 下载配置文件
mkdir hajimi && cd hajimi
wget https://raw.githubusercontent.com/wyeeeee/hajimi/main/wiki/docker/.env
wget https://raw.githubusercontent.com/wyeeeee/hajimi/main/wiki/docker/docker-compose.yaml

# 2. 编辑配置
nano .env
# 修改以下配置：
# GEMINI_API_KEYS=your_api_key_here
# PASSWORD=your_password_here

# 3. 启动服务
docker compose up -d

# 4. 访问服务
# 浏览器打开: http://localhost:7860
```

### 方案二：Hugging Face Spaces

1. **Fork 项目**
   - 访问 [GitHub 仓库](https://github.com/wyeeeee/hajimi)
   - 点击右上角 Fork 按钮

2. **构建镜像**
   - 在您 Fork 的仓库中，点击 Actions
   - 启用 workflows，运行 GHCR CI

3. **创建 Space**
   - 访问 [Hugging Face Spaces](https://huggingface.co/spaces)
   - 创建新的 Space，选择 Docker

4. **配置并部署**
   - 上传 Dockerfile
   - 配置环境变量
   - 等待部署完成

---

## 🔧 基础配置

无论选择哪种部署方式，都需要配置以下基础信息：

### 必需配置

```bash
# Gemini API 密钥（必填）
GEMINI_API_KEYS=your_api_key1,your_api_key2,your_api_key3

# 访问密码（必填）
PASSWORD=your_secure_password
```

::: tip 获取 API 密钥
访问 [Google AI Studio](https://makersuite.google.com/app/apikey) 免费获取 Gemini API 密钥
:::

### 常用可选配置

```bash
# 速率限制
MAX_REQUESTS_PER_MINUTE=30              # 每分钟最大请求数
MAX_REQUESTS_PER_DAY_PER_IP=600         # 每IP每日请求限制
API_KEY_DAILY_LIMIT=100                 # 每个API密钥每日限制

# 功能开关
FAKE_STREAMING=true                     # 假流式传输（避免超时）
RANDOM_STRING=true                      # 随机字符串伪装
SEARCH_MODE=false                       # 联网搜索模式

# 并发控制
CONCURRENT_REQUESTS=1                   # 默认并发数
MAX_CONCURRENT_REQUESTS=3               # 最大并发数

# 高级功能
ENABLE_VERTEX=false                     # 是否启用 Vertex AI
```

---

## 🎯 部署完成后

### 1. 验证部署

访问您的部署地址，应该看到 Hajimi 的登录界面：

- **本地部署**: `http://localhost:7860`
- **云端部署**: 您的分配域名

### 2. 登录管理界面

使用您配置的 `PASSWORD` 登录管理界面。

### 3. 测试 API

```bash
curl -X POST http://your-domain/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your_password" \
  -d '{
    "model": "gemini-pro",
    "messages": [{"role": "user", "content": "Hello, Hajimi!"}]
  }'
```

### 4. 接入客户端

在 SillyTavern 等客户端中配置：
- **API 类型**: 聊天补全
- **来源**: 自定义（兼容 OpenAI）
- **基础 URL**: `http://your-domain/v1`
- **API 密钥**: 您的密码

---

## 🆘 遇到问题？

如果部署过程中遇到问题，请查看：

- [故障排除指南](../usage/troubleshooting.md)
- [配置说明](../usage/configuration.md)
- [GitHub Issues](https://github.com/wyeeeee/hajimi/issues)

## 🚀 高级功能

部署成功后，您还可以：

- [配置 Vertex AI](./vertex.md) 获得更高配额
- [优化配置参数](../usage/configuration.md) 提升性能
- [设置监控](../usage/) 了解使用情况

---

::: tip 推荐阅读
- 新用户建议先阅读 [Docker 部署教程](./docker.md)
- 想要免费部署可查看 [Hugging Face 教程](./huggingface.md)
- 需要手机部署可参考 [Termux 教程](./termux.md)
:::

选择合适的部署方式，开始您的 Hajimi 之旅吧！