# OpenClaw Docker 镜像

**最干净的 OpenClaw Docker 镜像** — 自动跟踪官方 release，多架构支持，一键拉取，开箱即用。

## 镜像列表

| 镜像 | 标签 | 用途 | 大小 |
|------|------|------|------|
| 主镜像 | `ghcr.io/ashj-yf/openclaw-docker:latest` | OpenClaw 主程序 | ~1.2GB |
| Sandbox | `ghcr.io/ashj-yf/openclaw-docker:sandbox` | 基础沙盒容器 | ~200MB |
| Sandbox Browser | `ghcr.io/ashj-yf/openclaw-docker:sandbox-browser` | 带浏览器的沙盒 | ~800MB |
| Sandbox Common | `ghcr.io/ashj-yf/openclaw-docker:sandbox-common` | 完整开发环境沙盒 | ~2GB |

所有镜像支持 `amd64` 和 `arm64` 架构。

## 快速开始

### 使用 Docker Compose（推荐）

```bash
# 下载 docker-compose.yml
curl -O https://raw.githubusercontent.com/ashj-yf/openclaw-docker/main/docker-compose.yml

# 启动主服务
docker compose --profile main up -d

# 查看日志
docker compose logs -f openclaw

# 停止服务
docker compose down
```

### 启动不同服务

```bash
# 主服务
docker compose --profile main up -d

# 基础 Sandbox
docker compose --profile sandbox up -d

# 带浏览器的 Sandbox（支持 VNC 访问）
docker compose --profile sandbox-browser up -d

# 完整开发环境 Sandbox
docker compose --profile sandbox-common up -d

# 启动所有服务
docker compose --profile all up -d
```

### 使用 Docker 命令

```bash
# 拉取镜像
docker pull ghcr.io/ashj-yf/openclaw-docker:latest

# 运行容器
docker run -d --name openclaw \
  -p 18789:18789 \
  -v openclaw-data:/app/data \
  ghcr.io/ashj-yf/openclaw-docker:latest

# 查看日志
docker logs -f openclaw
```

## 本地构建

### 前置要求

- Docker 24.0+
- Docker Buildx
- 多架构支持需要 QEMU

### 使用构建脚本

```bash
# 克隆仓库
git clone https://github.com/ashj-yf/openclaw-docker.git
cd openclaw-docker

# 赋予执行权限
chmod +x build.sh

# 本地构建所有镜像
./build.sh

# 构建指定版本
./build.sh v2026.4.9

# 构建并推送到 ghcr.io
PUSH=true ./build.sh v2026.4.9

# 使用指定 OpenClaw 版本源码
OPENCLAW_VERSION=v2026.4.9 ./build.sh
```

### 使用 Docker Compose 本地构建

```bash
# 设置源码目录
export OPENCLAW_SRC=./openclaw-src

# 下载源码（首次）
curl -sL https://api.github.com/repos/openclaw/openclaw/tarball/latest | tar -xzf - -C openclaw-src --strip-components=1

# 构建并启动
docker compose --profile main up -d --build
```

## 服务说明

### 主服务 (openclaw)

OpenClaw 主程序，提供 AI 助手功能。

- **端口**: 18789
- **健康检查**: `/healthz`
- **数据持久化**: `/app/data`, `/app/skills`

### Sandbox

基础沙盒容器，用于安全执行代码。

- 基于 Debian bookworm-slim
- 包含基础工具：bash, curl, git, jq, python3, ripgrep

### Sandbox Browser

带浏览器的沙盒，支持自动化浏览器操作。

- **端口**:
  - 9222: Chrome DevTools Protocol
  - 5900: VNC
  - 6080: noVNC (Web VNC)
- 包含 Chromium 浏览器
- 支持 VNC 远程访问

### Sandbox Common

完整开发环境沙盒，包含：

- Node.js, npm, pnpm
- Python 3
- Go, Rust
- Bun
- Homebrew

## 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `IMAGE_REGISTRY` | `ghcr.io` | 镜像 Registry |
| `IMAGE_REPO` | `ashj-yf/openclaw-docker` | 仓库名称 |
| `IMAGE_TAG` | `latest` | 镜像标签 |
| `OPENCLAW_VERSION` | `latest` | OpenClaw 源码版本 |

## 版本列表

所有版本发布请查看 [Releases 页面](../../releases)。

## 许可证

MIT License — 与 OpenClaw 官方保持一致。

## 相关链接

- [OpenClaw 官方仓库](https://github.com/openclaw/openclaw)
- [OpenClaw 官方文档](https://docs.openclaw.ai)