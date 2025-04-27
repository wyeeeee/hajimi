# Hajimi 应用 Docker 部署指南 🚀

## 欢迎使用 Hajimi 应用！本指南将引导您使用 Docker 在不同环境（本地电脑、远程服务器、NAS）中快速部署 Hajimi 应用。

## 1. 准备工作 🛠️

### （一）安装 Docker
请确保您的系统（Windows, macOS, Linux）已安装 Docker Desktop，macOS 用户推荐安装[OrbStack](https://orbstack.dev/download)。
- **下载地址**：[Docker 官方网站](https://www.docker.com/get-started)
- **安装步骤**：按照官方指引完成安装。

### （二）获取配置文件
下载部署所需的两个核心配置文件：

**[.env文件下载](https://github.com/beijixingxing/hajimi/blob/main/wiki/docker/.env)**

**[docker-compose.yaml文件下载](https://github.com/beijixingxing/hajimi/blob/main/wiki/docker/docker-compose.yaml)**

### （三）创建项目目录并放置配置文件件 📂
在您选择的位置创建一个专门用于部署 Hajimi 的文件夹，并将下载的 .env 和 docker-compose.yaml 文件放入该文件夹中。
- **Mac/Linux**：在终端执行 `mkdir ~/hajimi-app && cd ~/hajimi-app`
- **Windows**：在命令提示符或 PowerShell 执行 `mkdir C:\Users\<用户名>\hajimi-app && cd C:\Users\<用户名>\hajimi-app` （请将 `<用户名>` 替换为您的 Windows 用户名）
或者，您也可以直接在桌面或其他位置创建 hajimi-app 文件夹，然后将下载的两个文件移动进去。

**重要提示**：后续的所有命令行操作，除非特别说明，都应在此 hajimi-app 文件夹内执行。

### （四）通用配置步骤  ⚙️
在启动服务之前，您需要根据自己的需求修改配置文件。请使用文本编辑器打开 hajimi-app 文件夹中的 .env 和 docker-compose.yaml 文件。
1. **修改 .env 文件**
这是存放敏感信息和应用基本配置的地方。
```
# --- 必填项 ---
# 设置你的 Gemini API 密钥，可以设置多个，用英文逗号隔开
GEMINI_API_KEYS=key1,key2,key3  # <= 替换为你的真实密钥

# 设置应用的登录密码
PASSWORD=123   # <= 设置一个安全的密码，默认密码123

# --- 可选项 (Vertex AI) ---
# 是否启用 Google Vertex AI (默认关闭)
ENABLE_VERTEX=false           # <= 如需开启，改为 true

# 如果开启 Vertex AI，请填入完整的 Google Cloud 服务账号 JSON 密钥内容
# 注意：整个 JSON 内容需要包含在英文单引号 ' ' 内部
GOOGLE_CREDENTIALS_JSON='JSON 密钥内容' # <= 粘贴你的 JSON 密钥内容
```
2. **按需修改 docker-compose.yaml 文件**
这个文件定义了 Docker 如何运行 Hajimi 服务。
    - **端口映射**：如果 7860 端口已被其他应用占用，您需要修改端口映射。
    - **网络代理**：如果您的部署环境无法直接访问 Google API (或其他所需外部服务)，需要配置代理。
```
services:
  hajimi:
    # ... (其他配置保持不变) ...
    ports:
      - "7860:7860" # 如果 7860 端口冲突，修改冒号左边的数字，例如 "17860:7860"
    environment:
      # --- 网络代理 (按需取消注释并修改) ---
      # 如果需要 HTTP 代理:
      # HTTP_PROXY: "http://your_proxy_address:port"  # <= 例如 "http://127.0.0.1:7890"
      # 如果需要 HTTPS 代理 (通常与 HTTP 代理相同):
      # HTTPS_PROXY: "http://your_proxy_address:port" # <= 例如 "http://127.0.0.1:7890"
      # ... (其他环境变量，如 .env 文件中的内容会自动加载) ...
```
配置完成后，请保存文件。

## 三、选择部署方式并启动服务 ▶️
根据您的环境选择相应的部署方式：
### （一）本地电脑部署 (Docker Desktop)
1. 打开终端 (Mac/Linux) 或命令提示符/PowerShell (Windows)。
2. 进入项目目录：使用 `cd` 命令切换到您之前创建的 hajimi-app 文件夹。
    - **示例 (Mac/Linux)**：`cd ~/hajimi-app`
    - **示例 (Windows)**：`cd C:\Users\<用户名>\hajimi-app`
3. 启动服务：执行以下命令以后台模式启动服务。
```
docker compose up -d
```
Docker 会自动拉取镜像并根据 docker-compose.yaml 和 .env 文件启动容器。

### （二）远程服务器部署 (SSH)
1. 使用 SSH 工具（如 ssh 命令、PuTTY、Termius 等）连接到您的远程服务器。
2. 创建并进入项目目录：
```
# 创建目录 (路径可自定义) 并进入该目录
mkdir -p /path/to/your/hajimi-app && cd /path/to/your/hajimi-app
# 例如: mkdir -p /opt/hajimi-app && cd /opt/hajimi-app
```
3. 直接下载配置文件
```bash
# 下载 .env 文件
wget https://raw.githubusercontent.com/beijixingxing/hajimi/main/wiki/docker/.env

# 下载 docker-compose.yml
wget https://raw.githubusercontent.com/beijixingxing/hajimi/main/wiki/docker/docker-compose.yaml
```
或使用curl：
```bash
curl -O https://raw.githubusercontent.com/beijixingxing/hajimi/main/wiki/docker/.env
curl -O https://raw.githubusercontent.com/beijixingxing/hajimi/main/wiki/docker/docker-compose.yaml
```
4. 验证文件
```bash
ls -l  # 应看到两个文件
cat .env  # 检查配置文件内容
```
5. 启动服务：在 SSH 终端中，确保您位于项目目录下，执行启动命令。
```
docker compose up -d
```

### （三）NAS 部署 (通过 Docker Compose UI)
注意：不同 NAS 品牌的 Docker UI（如群晖的 Container Manager, QNAP 的 Container Station）操作略有不同，以下为通用步骤。
1. 通过 NAS 的文件管理工具（如 File Station）在 Docker 应用的数据存储区（通常是 /volume1/docker/ 或类似路径）创建一个 hajimi 或 hajimi-app 文件夹。
2. 将本地修改好的 .env 和 docker-compose.yaml 文件上传到 NAS 上刚创建的文件夹中。
3. 打开 NAS 的 Docker 管理应用（如 Container Manager）。
4. 寻找 “项目” (Project)、“应用” (Application) 或 “Compose” 相关的选项。
5. 选择 “创建” (Create) 或 “导入” (Import)。
6. 设置项目名称（如 hajimi），并选择已上传 docker-compose.yaml 文件所在的文件夹路径。
7. 系统通常会自动识别 docker-compose.yaml 文件。确认配置无误后，点击 “创建”、“部署” 或 “运行”。
8. NAS 的 Docker UI 会根据配置文件拉取镜像并启动容器。

## 四、访问与验证 ✅
服务启动后，稍等片刻让应用完全启动。
1. **本地访问**：打开浏览器，访问 `http://localhost:7860`（如果您修改了端口，请使用修改后的端口）。
2. **服务器/NAS 访问**：打开浏览器，访问 `http://<服务器或NAS的IP地址>:7860`（请将 `<服务器或NAS的IP地址>` 替换为实际 IP，端口同样根据配置修改）。
3. **API 端点**：应用的 API (兼容 OpenAI 格式) 可以在以下地址访问：`http://<访问地址>:7860/v1`

看到登录界面并能使用您在 .env 文件中设置的 PASSWORD 成功登录，即表示部署成功！

## 五、常见问题与解决 (FAQ) ❓
### （一）Q1: 启动时提示端口已被占用 (Port is already allocated)
- **原因**：7860 端口（或其他您配置的端口）已被系统上另一个程序使用。
- **排查**：
    - **Mac/Linux**：在终端运行 `sudo lsof -i :7860`
    - **Windows**：在命令提示符或 PowerShell 运行 `netstat -ano | findstr "7860"`
- **解决方案**：
    - 停止占用该端口的程序。
    - 或者，修改 docker-compose.yaml 文件中的 ports 部分，将冒号左侧的 7860 改为其他未被占用的端口（如 17860），例如：`ports: - "17860:7860"`。保存后需要重新启动服务 (`docker-compose down` 然后 `docker-compose up -d`)。

### （二）Q2: 应用无法连接外部服务 (如 Google API)
- **原因**：部署环境的网络无法直接访问所需服务，通常需要设置网络代理。
- **解决方案**：
    - **确认代理**：确保您有可用的 HTTP/HTTPS 代理服务器地址和端口。
    - **配置代理**：编辑 docker-compose.yaml 文件，在 environment 部分取消 HTTP_PROXY 和 HTTPS_PROXY 的注释 (#)，并填入您的代理地址。例如:
```
environment:
  HTTP_PROXY: "http://192.168.1.100:7890"
  HTTPS_PROXY: "http://192.168.1.100:7890"
```
    - **重启服务**：保存文件后，在项目目录下执行 `docker-compose down` 然后 `docker-compose up -d`。
    - **无需代理**：如果您的网络环境不需要代理，请确保 HTTP_PROXY 和 HTTPS_PROXY 配置被注释掉（前面有 #）或直接删除。

## 六、更新指南 🔄
### （一）自动更新 (内置)
docker-compose.yaml 文件中已包含 Watchtower 服务，用于自动检测并更新 Hajimi 应用的 Docker 镜像。默认设置是每小时检查一次。如果检测到新版本，它会自动拉取并重启容器。

### （二）手动更新

如果您想立即更新到最新版本或禁用了自动更新，可以按以下步骤手动更新：
1. 进入项目目录：使用 `cd` 命令切换到包含 docker-compose.yaml 文件的目录。
```
# 示例 (路径需替换为您的实际路径)
cd /path/to/your/hajimi-app
```
2. 拉取最新镜像：
```
docker-compose pull
```
这将只拉取 docker-compose.yaml 文件中定义的服务的新镜像版本（如果存在）。
3. 停止并重新创建容器：
```
# 停止当前运行的容器
docker-compose down
# 使用新镜像重新创建并启动容器
docker-compose up -d
```
或者，更简洁的方式是直接执行 `docker-compose up -d`，Compose 会自动检测到镜像已更新并重新创建容器。

4. **可选的强制清理命令（仅在遇到问题时使用）**：
```
# 停止并删除容器、网络，并删除旧镜像
# docker-compose down --rmi all
# 然后重新拉取并启动
# docker-compose pull
# docker-compose up -d
```

**建议**：首次部署时，尽量使用默认配置（除了必要的 API 密钥和密码），确保服务能正常运行。稳定运行后，再根据需要调整端口、代理或其他高级配置。 
