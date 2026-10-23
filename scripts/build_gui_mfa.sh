#!/usr/bin/env bash
# =============================================================================
# MaaEOV GUI 构建脚本
#   从 MFAAvalonia 上游源码编译 self-contained 单文件 MaaEOV.exe（win-x64）
#
# 用法（可用环境变量覆盖默认值）：
#   MFA_SRC=...  MFA_OUT=...  MFA_VER=2.16.1  bash scripts/build_gui_mfa.sh
#
# 依赖：.NET SDK 10+、MFAAvalonia 源码仓库、可访问 nuget.org / maaxyz.github.io
#
# ⚠️ 关键坑（血泪教训，勿改）：
#   1. 必须 -p:DisableBeauty=True
#      NetBeauty 会把 STARTUP_HOOKS=libloader 写进 runtimeconfig，
#      但单文件模式下该程序集没被打包 → 启动即崩：
#      "Startup hook assembly 'libloader' failed to load" (0xE0434352)
#      注意：-p:BeautyOnPublishOnly=false 是错的做法，它会让 NetBeauty 在 build
#      阶段也运行，污染 runtimeconfig，反而加剧问题。
#   2. 不要改 AssemblyName。源码里有 26 处 avares://MFAAvalonia.Core/... 资源 URI
#      硬依赖程序集名，改名会导致运行时资源加载失败。程序名只能靠编译后重命名 exe。
#   3. -p:EnableCompressionInSingleFile=true 能把 exe 从 191MB 压到 ~95MB。
#   4. --configfile 必须显式指定：NuGet.Config 在 MFAAvalonia/ 子目录，
#      不会自动被读取；Maa.* 包需要 maaxyz.github.io 源。
#   5. 在受限沙箱/安全策略环境下构建可能报 "Access to the path ... is denied"，
#      此时需要获得非沙箱执行权限后再跑。
#   6. -p:Brand=MaaEOV（2026-10-23 加）**只在 MFA_SRC 指向定制分支时才有意义**。
#      本脚本默认指向 vendor/MFAAvalonia —— 上游 tag 的独立副本，不含任何定制代码，
#      此时该参数被 MSBuild 静默忽略（无害）。若临时把 MFA_SRC 指到含定制的分支
#      （如 Maadori 的 maadori-custom），**必须保留该参数**，否则会走「兼容模式」
#      = 定制功能全开，产物里带出 QQ 机器人设置页、成绩图推送、日志图。
# =============================================================================
set -euo pipefail

# 由脚本自身位置推导项目根，避免写死 C:/Users/Lee/...（换机、换目录、换用户名即失效）
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# 默认使用项目内的**独立副本**，不再指向 C:/Users/Lee/Documents/Python/MFAAvalonia。
# 那份是 Maadori 独享的构建源（含 2603 行定制，且分支状态随开发变动），
# MaaEOV 依赖它会出现「上游 tag 里混进别人定制」「切分支把别人状态带走」两类问题。
SRC="${MFA_SRC:-$PROJECT_ROOT/vendor/MFAAvalonia}"
OUT="${MFA_OUT:-$PROJECT_ROOT/.mfa_build/win-x64}"
VER="${MFA_VER:-1.1.0}"
ICON="${MFA_ICON:-$PROJECT_ROOT/Assets/logo.ico}"
DOTNET="${DOTNET:-/c/Program Files/dotnet/dotnet.exe}"

if [ ! -f "$SRC/MFAAvalonia.Desktop/MFAAvalonia.Desktop.csproj" ]; then
  echo "错误：MFA 源码不存在或不是 MFAAvalonia 仓库" >&2
  echo "  实际路径：$SRC" >&2
  echo "  首次使用请先初始化副本：" >&2
  echo "    bash scripts/sync_mfa_src.sh v2.16.1" >&2
  exit 1
fi

SRC_VERSION="$(git -C "$SRC" describe --tags --always --dirty 2>/dev/null || echo '未知（非 git 仓库）')"
SRC_DIRTY=""
if [ -n "$(git -C "$SRC" status --porcelain 2>/dev/null)" ]; then
  SRC_DIRTY="  ⚠️ 工作区有未提交改动，产物可能不可复现"
fi

echo "源码仓库 : $SRC"
echo "源码版本 : $SRC_VERSION$SRC_DIRTY"
echo "输出目录 : $OUT"
echo "版本号   : $VER"
echo "图标     : $ICON"
echo

cd "$SRC"

"$DOTNET" publish "MFAAvalonia.Desktop/MFAAvalonia.Desktop.csproj" \
  -c Release -r win-x64 \
  --configfile "$SRC/MFAAvalonia/NuGet.Config" \
  -p:SelfContained=true \
  -p:PublishSingleFile=true \
  -p:EnableCompressionInSingleFile=true \
  -p:PublishTrimmed=false \
  -p:PublishReadyToRun=false \
  -p:DisableBeauty=True \
  -p:DebugType=none \
  -p:DebugSymbols=false \
  -p:Brand=MaaEOV \
  -p:ApplicationIcon="$ICON" \
  -p:AssemblyTitle=MaaEOV \
  -p:Product=MaaEOV \
  -p:Company=MaaEOV \
  -p:Version="$VER" \
  -o "$OUT"

echo
echo "构建完成。产物在：$OUT"
echo
echo "================ 部署 + 升级后必做 ================"
echo "1) 复制产物到 MaaEOV 根目录，并把 MFAAvalonia.exe 改名为 MaaEOV.exe"
echo "   （新版 native 库位于 runtimes/win-x64/native/，务必先删掉根目录平铺的旧 dll）"
echo
echo "2) 【必做】把内嵌 Python 的 maafw 升到与框架同版本，否则 agent 永远连不上："
echo "     ./python/python.exe -m pip install --no-cache-dir \"maafw==<Maa.Framework.Runtimes 的版本>\""
echo "   验证方式：两侧 MaaAgentServer.dll 大小应完全一致："
echo "     ls -la python/Lib/site-packages/maa/bin/MaaAgentServer.dll"
echo "     ls -la runtimes/win-x64/native/MaaAgentServer.dll"
echo "   版本不对时的现象：日志卡在「正在启动 Agent(耗时可能较久)」，"
echo "   maafw.log 末尾停在 MaaAgentClientConnect，无任何报错（静默挂起）。"
echo
echo "3) 【必做】pipeline 语法迁移（v5 起 interrupt 已废弃）："
echo "     python scripts/migrate_pipeline_v5.py resource/base/pipeline"
echo "   不迁移的现象：日志报「资源加载失败！」（GUI 会提示「请删除整个文件夹重新下载」，属误导）。"
echo
echo "4) 校验：python scripts/verify_feature.py  → RESULT: ALL_OK"
echo "=================================================="
