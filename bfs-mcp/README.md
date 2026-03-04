# bfs-mcp

MCP server for [betfunsports.com](https://betfunsports.com) — gives AI agents full access to a P2P sports prediction platform through a headless browser.

The agent reads [`skill.md`](skill.md) to learn the platform, then uses 21 MCP tools to register, authenticate, browse events, place bets, and analyze results.

## Install

```bash
pip install git+https://github.com/elesingp2/bfs-knowledge.git#subdirectory=bfs-mcp
playwright install --with-deps chromium
```

## Usage with Claude / Cursor

Add to your MCP config:

```json
{
  "mcpServers": {
    "bfs": {
      "command": "bfs-mcp"
    }
  }
}
```

**Claude Desktop:** `~/Library/Application Support/Claude/claude_desktop_config.json`
**Cursor:** Settings → MCP → Add Server

The agent automatically receives `skill.md` as MCP instructions — it knows the platform, all tools, and the betting workflow.

## Tools

### Platform API

| Tool | Description |
|------|-------------|
| `bfs_register` | Register new account (gets 100 free BFS) |
| `bfs_confirm_registration` | Activate account via email confirmation link |
| `bfs_login` | Authenticate |
| `bfs_logout` | End session |
| `bfs_auth_status` | Check auth + EUR/BFS balances |
| `bfs_coupons` | List available sports coupons |
| `bfs_coupon_details` | Events, outcomes, rooms for a coupon |
| `bfs_place_bet` | Place a bet |
| `bfs_active_bets` | Active bets (pending results) |
| `bfs_bet_history` | Full history as CSV |
| `bfs_account` | Account details |
| `bfs_payment_methods` | Deposit/withdrawal methods |

### Page tools

| Tool | Description |
|------|-------------|
| `page_open` | Navigate to URL |
| `page_read` | Read page content |
| `page_click` | Click element |
| `page_fill` | Fill form field |
| `page_select` | Select dropdown |
| `page_screenshot` | Visual snapshot |
| `page_run_script` | Execute JS |
| `page_forms` | List forms |
| `page_links` | List links |

## Telegram Bot

Optional standalone bot that wraps the same browser engine with an LLM agent:

```bash
pip install "bfs-mcp[bot]"

export BFS_TG_TOKEN=...       # Telegram bot token
export BFS_LLM_KEY=...        # OpenRouter / OpenAI API key
export BFS_LLM_MODEL=deepseek/deepseek-chat

bfs-bot
```

## How Betfunsports works

P2P sports prediction platform. Player bets form a prize pool — **fully distributed** among winners.

- **Win rate:** top 50% of bets win (ranked by accuracy 0–100)
- **100-point rule:** perfect predictions always win
- **Min coefficient:** 1.3
- **Sports:** Football, Tennis, Hockey, Basketball, F1, Biathlon, Volleyball, Boxing, MMA

| Room | Currency | Range | Fee |
|------|----------|-------|-----|
| Wooden | BFS (free) | 1–10 | 0% |
| Bronze | EUR | 1–5 | 10% |
| Silver | EUR | 10–50 | 7.5% |
| Golden | EUR | 100–500 | 5% |

## Architecture

```
src/bfs_mcp/
├── browser.py   ← Playwright engine (headless Chromium)
├── server.py    ← MCP server, 21 tools
└── bot.py       ← Telegram LLM agent (optional)
```

## License

MIT
