---
home: true
heroImage: /logo.png
heroText: Hajimi
tagline: 高性能 Gemini API 反向代理服务
actionText: 快速开始 →
actionLink: /deploy/
features:
- title: 🚀 多平台部署
  details: 支持 Docker、云端、移动端等多种部署方式，满足不同场景需求
- title: 🔒 安全可靠
  details: 内置访问控制、速率限制、白名单等安全机制，保障服务稳定
- title: 🎨 易于使用
  details: 提供友好的 Web UI 和完整的 API 文档，快速上手
footer: MIT Licensed | Copyright © 2024 Hajimi
---

# 欢迎使用 Hajimi

Hajimi 是一个高性能、功能丰富的 Gemini API 反向代理服务，提供多种部署方式和强大的功能特性。

## ✨ 核心特性

- **多平台支持** - Docker、Hugging Face、Zeabur、Termux 等
- **高性能** - 支持并发请求和智能缓存
- **安全可靠** - 访问控制、速率限制、白名单功能
- **功能丰富** - 流式传输、联网搜索、Vertex AI 集成
- **易于使用** - 友好的 Web UI 和详细文档

## 🚀 快速部署

选择适合您的部署方式：

::: tip Docker 部署（推荐）
适合本地开发和服务器部署
```bash
docker compose up -d
```
[查看详细教程](/deploy/docker.md)
:::

::: tip 免费云端部署
无需服务器，完全免费
- [Hugging Face Spaces](/deploy/huggingface.md)
- [Claw Cloud](/deploy/claw.md)
- [Zeabur](/deploy/zeabur.md)
:::

::: tip Android 部署
在手机上运行 Hajimi
```bash
# Termux + Ubuntu
bash ubuntu22.sh
```
[查看详细教程](/deploy/termux.md)
:::

## 📖 使用指南

- [基础配置](/usage/configuration.md)
- [故障排除](/usage/troubleshooting.md)
- [API 文档](/usage/)

## 🔗 相关链接

- [GitHub 仓库](https://github.com/wyeeeee/hajimi)
- [问题反馈](https://github.com/wyeeeee/hajimi/issues)
- [获取 Gemini API 密钥](https://makersuite.google.com/app/apikey)