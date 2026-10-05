#!/bin/bash
# ==============================================================================
# 1Panel 本地应用一键同步脚本 (1Panel Community Apps Sync Script)
#
# 支持直接在已安装仓库中执行，亦支持通过 curl 一键远程执行：
#   curl -sSL https://raw.githubusercontent.com/mainsir/1panel-apps/main/scripts/sync-to-1panel.sh | bash
# ==============================================================================
set -euo pipefail

REPO_URL="${REPO_URL:-https://github.com/mainsir/1panel-apps.git}"
LOCAL_DIR="${LOCAL_DIR:-/opt/1panel/resource/apps/local}"

mkdir -p "$LOCAL_DIR"

if [ -d "/opt/1panel-apps/.git" ] && [ "${USE_TMP:-0}" != "1" ]; then
  # 已有长期仓库目录，直接拉取更新并同步
  echo "[*] 检测到本地已有仓库 /opt/1panel-apps，正在拉取最新代码..."
  git -C /opt/1panel-apps pull --ff-only 2>/dev/null || (cd /opt/1panel-apps && git fetch --depth=1 && git reset --hard origin/main)
  cp -rf /opt/1panel-apps/apps/* "$LOCAL_DIR"/
else
  # 临时目录克隆，复制完毕后自动打扫清理
  TMP_DIR=$(mktemp -d /tmp/1panel-apps-sync-XXXXXX)
  trap 'rm -rf "$TMP_DIR"' EXIT
  echo "[*] 正在从 $REPO_URL 拉取最新应用包..."
  git clone --depth 1 "$REPO_URL" "$TMP_DIR" -q
  echo "[*] 正在同步应用至 1Panel 本地应用目录: $LOCAL_DIR"
  cp -rf "$TMP_DIR"/apps/* "$LOCAL_DIR"/
fi

echo "================================================================================"
echo "[OK] 同步成功！($(date '+%Y-%m-%d %H:%M:%S'))"
echo "[提示] 请打开 1Panel 管理面板 ->「应用商店」-> 点击右上角「更新应用列表」"
echo "       切换到「本地」分类即可安装使用！"
echo "================================================================================"
