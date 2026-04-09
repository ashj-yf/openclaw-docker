# OpenClaw Docker 镜像

**最干净的 OpenClaw Docker 镜像** — 自动跟踪官方 release，多架构支持，一键拉取，开箱即用。

## 特性

- ✅ **自动跟踪官方版本** — 每小时检查 OpenClaw 官方 release，自动构建新版本
- ✅ **多架构支持** — 同时支持 `amd64`（Intel/AMD）和 `arm64`（Apple Silicon / Raspberry Pi）
- ✅ **中文 Release Notes** — 每个版本的更新说明翻译成中文，便于阅读
- ✅ **内置浏览器支持** — 预装 Playwright Chromium，支持自动化场景
- ✅ **干净构建** — 使用官方 Dockerfile，无任何修改

## 快速开始

```bash
# 拉取最新版本
docker pull <registry>/openclaw:latest

# 运行容器
docker run -d --name openclaw \
  -p 18789:18789 \
  <registry>/openclaw:latest

# 查看日志
docker logs -f openclaw
```

## 版本列表

所有版本发布请查看 [Releases 页面](../../releases)。

每个 release 包含：
- 中文版更新说明
- 镜像下载地址
- 架构信息
- 快速使用命令

## 配置说明

### Registry 配置

镜像推送目标通过 GitHub Secrets 配置：

| Secret | 说明 | 示例 |
|--------|------|------|
| `DOCKER_REGISTRY` | Registry 地址 | `docker.io` / `ghcr.io` |
| `DOCKER_USERNAME` | Registry 用户名 | `yourusername` |
| `DOCKER_PASSWORD` | Registry 密码/Token | `xxx` |
| `DOCKER_IMAGE_NAME` | 镜像名称（可选） | `openclaw` |

### 翻译配置（可选）

如需启用 release notes 中文翻译，配置：

| Secret | 说明 |
|--------|------|
| `ANTHROPIC_API_KEY` | Claude API Key |

未配置时，release notes 将保留英文原文。

## 手动触发构建

在 Actions 页面可以手动触发 `build-image.yml` workflow，指定版本号进行构建。

## 架构说明

镜像使用官方 Dockerfile 构建，基础镜像为 `node:24-bookworm`，包含：
- Node.js 24 运行时
- Playwright Chromium（用于浏览器自动化）
- Docker CLI（可选，用于容器管理）

## 许可证

MIT License — 与 OpenClaw 官方保持一致。

## 相关链接

- [OpenClaw 官方仓库](https://github.com/openclaw/openclaw)
- [OpenClaw 官方文档](https://docs.openclaw.ai)