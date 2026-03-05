#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────────────
# BFS Agent Launcher
#
# Usage:
#   ./start.sh                     — start the Telegram bot only
#   ./start.sh --demo              — run the full demo betting loop
#   ./start.sh email password      — login + start bot (first-time setup)
# ──────────────────────────────────────────────────────────────────────

set -e

# ── Bot token must be set ──────────────────────────────────────────────
: "${BFS_TG_TOKEN:?Set BFS_TG_TOKEN before running. Example:}"
echo "Using bot token: ${BFS_TG_TOKEN:0:10}…"

# ── PATH fix for pip user-installs ────────────────────────────────────
export PATH="$PATH:$HOME/.local/bin"

# ── Install check ─────────────────────────────────────────────────────
if ! command -v bfs-mcp &>/dev/null; then
  echo "Installing bfs-mcp…"
  pip install -q git+https://github.com/elesingp2/betfunsports-mcp.git
  playwright install --with-deps chromium
fi

if ! python3 -c "import bfs_bot" 2>/dev/null; then
  echo "Installing bfs-bot (Telegram notifications)…"
  pip install -q git+https://github.com/elesingp2/betfunsports-telegram-bot.git
fi

# ── First-time login ───────────────────────────────────────────────────
if [[ "$1" =~ ^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$ ]]; then
  EMAIL="$1"
  PASSWORD="${2:?Password required as second argument}"
  echo ""
  echo "Logging in as $EMAIL …"
  python3 - <<PYEOF
import asyncio, json
from bfs_mcp.browser import BFSBrowser
async def _login():
    b = BFSBrowser()
    await b.start()
    r = await b.login("$EMAIL", "$PASSWORD")
    print(json.dumps(r, indent=2, ensure_ascii=False))
    await b.stop()
asyncio.run(_login())
PYEOF
fi

# ── Demo mode ─────────────────────────────────────────────────────────
if [[ "$1" == "--demo" ]]; then
  echo ""
  echo "Running demo betting loop…"
  python3 "$(dirname "$0")/test_bfs.py"
  exit 0
fi

# ── Start Telegram bot ────────────────────────────────────────────────
echo ""
echo "╔══════════════════════════════════════════════════╗"
echo "║  BFS Telegram Bot is running                     ║"
echo "║                                                  ║"
echo "║  1. Open Telegram                                ║"
echo "║  2. Find @bfs_mcp_bot                            ║"
echo "║  3. Send /start                                  ║"
echo "║                                                  ║"
echo "║  After that, your agent will send you live       ║"
echo "║  notifications for every login, bet, and result. ║"
echo "╚══════════════════════════════════════════════════╝"
echo ""

exec bfs-bot
