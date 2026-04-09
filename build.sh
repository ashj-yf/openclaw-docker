#!/bin/bash
# OpenClaw Docker 本地构建脚本

set -e

# 配置
REGISTRY="${IMAGE_REGISTRY:-ghcr.io}"
REPO="${IMAGE_REPO:-ashj-yf/openclaw-docker}"
TAG="${IMAGE_TAG:-latest}"
VERSION="${1:-local}"
PLATFORMS="${PLATFORMS:-linux/amd64,linux/arm64}"
OPENCLAW_VERSION="${OPENCLAW_VERSION:-}"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查依赖
check_dependencies() {
    log_info "检查依赖..."

    if ! command -v docker &> /dev/null; then
        log_error "Docker 未安装"
        exit 1
    fi

    if ! docker buildx version &> /dev/null; then
        log_error "Docker Buildx 未安装"
        exit 1
    fi

    log_info "依赖检查通过"
}

# 下载 OpenClaw 源码
download_source() {
    local version="${OPENCLAW_VERSION:-latest}"

    if [ -d "openclaw-src" ]; then
        log_info "openclaw-src 目录已存在，跳过下载"
        return
    fi

    log_info "下载 OpenClaw 源码 (version: ${version})..."

    local url="https://api.github.com/repos/openclaw/openclaw/tarball/${version}"

    curl -sL "$url" -o openclaw-source.tar.gz
    mkdir -p openclaw-src
    tar -xzf openclaw-source.tar.gz -C openclaw-src --strip-components=1
    rm openclaw-source.tar.gz

    log_info "源码下载完成"
}

# 构建镜像
build_image() {
    local name="$1"
    local dockerfile="$2"
    local tag_suffix="$3"
    shift 3
    local build_args=("$@")

    log_info "构建 ${name} 镜像..."

    local tags="${REGISTRY}/${REPO}:${tag_suffix}"
    if [ -n "$VERSION" ] && [ "$VERSION" != "local" ]; then
        tags="${tags},${REGISTRY}/${REPO}:${tag_suffix}-${VERSION}"
    fi

    local build_cmd=(
        docker buildx build
        --platform "${PLATFORMS}"
        --tag "${tags}"
        --file "openclaw-src/${dockerfile}"
        --push "${PUSH:-false}"
        --provenance false
    )

    for arg in "${build_args[@]}"; do
        build_cmd+=(--build-arg "$arg")
    done

    build_cmd+=("openclaw-src")

    "${build_cmd[@]}"

    log_info "${name} 镜像构建完成"
}

# 主函数
main() {
    log_info "OpenClaw Docker 本地构建"
    log_info "Registry: ${REGISTRY}"
    log_info "Repository: ${REPO}"
    log_info "Tag: ${TAG}"
    log_info "Platforms: ${PLATFORMS}"
    log_info "Version: ${VERSION}"
    echo ""

    check_dependencies
    download_source
    echo ""

    # 构建顺序：sandbox -> sandbox-common（依赖 sandbox）
    log_info "开始构建镜像..."
    echo ""

    # 1. 构建主镜像
    build_image "Main" "Dockerfile" "latest" "OPENCLAW_INSTALL_BROWSER=1"
    echo ""

    # 2. 构建 sandbox
    build_image "Sandbox" "Dockerfile.sandbox" "sandbox"
    echo ""

    # 3. 构建 sandbox-browser
    build_image "Sandbox Browser" "Dockerfile.sandbox-browser" "sandbox-browser"
    echo ""

    # 4. 构建 sandbox-common（依赖 sandbox）
    # 先 tag sandbox 为 bookworm-slim
    docker buildx imagetools create \
        --tag "${REGISTRY}/${REPO}:bookworm-slim" \
        "${REGISTRY}/${REPO}:sandbox" 2>/dev/null || true

    build_image "Sandbox Common" "Dockerfile.sandbox-common" "sandbox-common" \
        "BASE_IMAGE=${REGISTRY}/${REPO}:bookworm-slim"
    echo ""

    log_info "所有镜像构建完成！"
    echo ""
    log_info "镜像列表："
    echo "  - ${REGISTRY}/${REPO}:latest"
    echo "  - ${REGISTRY}/${REPO}:sandbox"
    echo "  - ${REGISTRY}/${REPO}:sandbox-browser"
    echo "  - ${REGISTRY}/${REPO}:sandbox-common"
}

# 使用帮助
show_help() {
    echo "OpenClaw Docker 本地构建脚本"
    echo ""
    echo "用法: $0 [VERSION] [OPTIONS]"
    echo ""
    echo "参数:"
    echo "  VERSION       版本标签 (默认: local)"
    echo ""
    echo "环境变量:"
    echo "  IMAGE_REGISTRY    Registry 地址 (默认: ghcr.io)"
    echo "  IMAGE_REPO        仓库名称 (默认: ashj-yf/openclaw-docker)"
    echo "  IMAGE_TAG         镜像标签 (默认: latest)"
    echo "  PLATFORMS         构建平台 (默认: linux/amd64,linux/arm64)"
    echo "  OPENCLAW_VERSION  OpenClaw 版本/分支 (默认: latest)"
    echo "  PUSH              是否推送镜像 (默认: false)"
    echo ""
    echo "示例:"
    echo "  $0                          # 本地构建所有镜像"
    echo "  $0 v2026.4.9                # 构建指定版本"
    echo "  PUSH=true $0 v2026.4.9      # 构建并推送"
    echo "  OPENCLAW_VERSION=v2026.4.9 $0  # 使用指定 OpenClaw 版本源码"
}

if [ "$1" = "-h" ] || [ "$1" = "--help" ]; then
    show_help
    exit 0
fi

main "$@"