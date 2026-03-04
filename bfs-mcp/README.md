# bfs-mcp

Platform API for [betfunsports.com](https://betfunsports.com) — lets AI agents autonomously browse sports events, place bets, and earn money.

Works as an MCP server (Claude, Cursor, OpenClaw, any MCP client) and as a standalone Telegram bot.

## Install

```bash
pip install git+https://github.com/elesingp2/bfs-knowledge.git#subdirectory=bfs-mcp
playwright install chromium
```

## MCP Server

```bash
bfs-mcp
```

Runs on stdio. Add to **Claude Desktop** (`claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "bfs": {
      "command": "bfs-mcp"
    }
  }
}
```

**Cursor** (Settings → MCP → Add):
```json
{
  "mcpServers": {
    "bfs": {
      "command": "bfs-mcp"
    }
  }
}
```

The agent gets 19 tools + full platform instructions. See [`skill.md`](skill.md) for the autonomous earning guide.

## Telegram Bot

```bash
pip install "bfs-mcp[bot]"

export BFS_TG_TOKEN=...                          # Telegram bot token
export BFS_LLM_KEY=...                           # OpenRouter API key
export BFS_LLM_MODEL=deepseek/deepseek-chat      # ~$0.0002/request

bfs-bot
```

Write naturally: "залогинься", "покажи купоны", "поставь на победу хозяев на Silver столе".

## How Betfunsports works

P2P sports prediction platform. Player bets form a prize pool — **fully distributed** among winners.

| | |
|-|-|
| **Win rate** | Top 50% of bets win |
| **Ranking** | Accuracy (0-100) → bet size → time |
| **Min coefficient** | 1.3 |
| **100-point rule** | Perfect predictions always win |

### Rooms

| Room | Currency | Range | Fee |
|------|----------|-------|-----|
| Wooden | BFS (free) | 1-10 | 0% |
| Bronze | EUR | 1-5 | 10% |
| Silver | EUR | 10-50 | 7.5% |
| Golden | EUR | 100-500 | 5% |

## Tools (19)

### Platform API
| Tool | What it does |
|------|-------------|
| `bfs_login` | Authenticate |
| `bfs_logout` | End session |
| `bfs_auth_status` | Balances (EUR, BFS) |
| `bfs_coupons` | Available sports/coupons |
| `bfs_coupon_details` | Events, outcomes, rooms |
| `bfs_place_bet` | Place a bet |
| `bfs_bet_history` | **Export bets as CSV** for analysis |
| `bfs_account` | Account details |
| `bfs_payment_methods` | Deposit/withdrawal info |

### Page tools
| Tool | What it does |
|------|-------------|
| `page_open` | Navigate |
| `page_read` | Read content |
| `page_click` | Click |
| `page_fill` | Fill field |
| `page_select` | Dropdown |
| `page_screenshot` | Snapshot |
| `page_script` | Run script |
| `page_forms` | List forms |
| `page_links` | List links |

## Architecture

```
src/bfs_mcp/
├── browser.py   ← core engine (210 lines)
├── server.py    ← MCP server, 19 tools (150 lines)
└── bot.py       ← Telegram LLM agent (200 lines)
```

## Env vars (bot only)

| Variable | Required | Default |
|----------|----------|---------|
| `BFS_TG_TOKEN` | yes | — |
| `BFS_LLM_KEY` | yes | — |
| `BFS_LLM_BASE` | no | `https://openrouter.ai/api/v1` |
| `BFS_LLM_MODEL` | no | `deepseek/deepseek-chat` |
| `BFS_MAX_HISTORY` | no | `30` |
| `BFS_MAX_ITER` | no | `8` |
