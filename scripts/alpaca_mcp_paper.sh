#!/usr/bin/env bash
set -euo pipefail
export PATH="/usr/local/bin:$PATH"
export UV_CACHE_DIR=/var/lib/forge-uv/cache
export UV_TOOL_DIR=/var/lib/forge-uv/tools
export XDG_CACHE_HOME=/var/lib/forge-uv/cache
export XDG_DATA_HOME=/var/lib/forge-uv/share
mkdir -p "$UV_CACHE_DIR" "$UV_TOOL_DIR" "$XDG_DATA_HOME"
set -a
source /etc/forge/forge.env
set +a
export ALPACA_API_KEY="${APCA_API_KEY_ID:?}"
export ALPACA_SECRET_KEY="${APCA_API_SECRET_KEY:?}"
export ALPACA_PAPER_TRADE=true
export ALPACA_TOOLSETS="${ALPACA_TOOLSETS:-account,trading,watchlists,assets,stock-data,crypto-data,options-data,news,corporate-actions}"
exec uvx alpaca-mcp-server --transport "${1:-stdio}"
