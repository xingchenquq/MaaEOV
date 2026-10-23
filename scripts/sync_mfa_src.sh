#!/usr/bin/env bash
# =============================================================================
# 同步 MaaEOV 专用的 MFAAvalonia 源码副本（vendor/MFAAvalonia）
#
# 用法：
#   bash scripts/sync_mfa_src.sh v2.16.1
#   MFA_LOCAL_MIRROR=D:/other/MFAAvalonia bash scripts/sync_mfa_src.sh v2.16.1
#
# 行为：
#   首次 → 从本地镜像克隆（离线可用，几十秒）；镜像不存在则退回 GitHub
#   后续 → fetch 该 tag 并 checkout（detached HEAD，不建分支，不留本地修改）
#
# 为什么要有这个副本：
#   `C:/Users/Lee/Documents/Python/MFAAvalonia` 是 **Maadori 独享**的构建源，
#   停在 maadori-custom 分支、含 2603 行定制。MaaEOV 直接用它会有两个问题：
#     (a) 产物里带出 Maadori 专属功能（QQ 机器人通知、成绩图推送、日志图）；
#     (b) 升级时 `git checkout <tag>` 会把 Maadori 的分支状态切走，
#         下次打 Maadori 包就静默丢功能。
#   独立副本把这两个问题一起切断：与主工作区零共享。
# =============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
DEST="$PROJECT_ROOT/vendor/MFAAvalonia"

UPSTREAM_URL="https://github.com/MaaXYZ/MFAAvalonia.git"
#: 首次克隆的本地源；不存在时自动退回 GitHub。可用环境变量覆盖。
LOCAL_MIRROR="${MFA_LOCAL_MIRROR:-C:/Users/Lee/Documents/Python/MFAAvalonia}"

TAG="${1:-}"
if [ -z "$TAG" ]; then
    echo "用法：bash scripts/sync_mfa_src.sh <tag>    例：v2.16.1"
    echo "环境变量：MFA_LOCAL_MIRROR=<本地 MFAAvalonia 仓库路径>（仅首次克隆时使用）"
    exit 1
fi

# ---- 1. 首次初始化 ----
if [ ! -d "$DEST/.git" ]; then
    echo "== 首次初始化 vendor/MFAAvalonia =="
    if [ -d "$LOCAL_MIRROR/.git" ]; then
        echo "   从本地镜像克隆：$LOCAL_MIRROR"
        # --no-hardlinks：真正复制对象，避免主仓库被移动/删除后副本损坏
        git clone --no-hardlinks "$LOCAL_MIRROR" "$DEST"
        git -C "$DEST" remote set-url origin "$UPSTREAM_URL"
        git -C "$DEST" remote add mine "https://github.com/xingchenquq/MFAAvalonia-maadori.git" 2>/dev/null || true
    else
        echo "   本地镜像不存在，从 GitHub 克隆：$UPSTREAM_URL"
        git clone "$UPSTREAM_URL" "$DEST"
    fi
fi

cd "$DEST"

# ---- 2. 切到目标 tag ----
echo "== 切换到 $TAG =="
if ! git rev-parse --verify --quiet "refs/tags/$TAG" >/dev/null; then
    echo "   本地无该 tag，尝试 fetch ..."
    if ! git fetch origin "refs/tags/$TAG:refs/tags/$TAG"; then
        echo "错误：fetch 失败，且本地也不存在 tag '$TAG'" >&2
        echo "  本地最近的 tag：" >&2
        git tag --sort=-creatordate | head -10 >&2
        exit 1
    fi
fi

git checkout "$TAG" >/dev/null 2>&1 || { echo "错误：checkout $TAG 失败" >&2; exit 1; }

# ---- 3. 干净性检查 ----
# 副本里出现未提交改动，说明有人在里面直接改了源码 —— 产物将不可复现，
# 且下次 checkout 会带着改动或被拒绝。这里显式告警而不是静默继续。
if [ -n "$(git status --porcelain)" ]; then
    echo "⚠️  vendor 工作区有未提交改动（产物不可复现）：" >&2
    git status --short >&2
    echo "   还原：git -C \"$DEST\" checkout -- ." >&2
fi

# ---- 4. 解析框架版本，供 Python 绑定对齐 ----
FRAMEWORK_VER="$(sed -nE 's/.*Include="Maa\.Framework\.Runtimes" Version="([^"]+)".*/\1/p' \
                 MFAAvalonia/MFAAvalonia.csproj | head -1)"

echo
echo "== 就绪 =="
echo "   路径       : $DEST"
echo "   版本       : $(git describe --tags --always)"
echo "   提交       : $(git log -1 --format='%h %s')"
echo "   MaaFw 版本 : ${FRAMEWORK_VER:-未解析到}"
echo
echo "MaaEOV 的 Python 绑定必须同版本，否则代理模式会出难以定位的崩溃："
echo "   ./python/python.exe -m pip install --no-cache-dir \"maafw==${FRAMEWORK_VER:-<上值>}\""
