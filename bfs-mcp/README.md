# bfs-mcp

MCP server + Telegram bot for [betfunsports.com](https://betfunsports.com) — headless browser bridge, no API needed.

An AI agent controls the real website through Playwright, enabling login, browsing sports, and placing bets via natural language.

## Quick start

### Install

```bash
pip install git+https://github.com/elesingp2/bfs-knowledge.git#subdirectory=bfs-mcp
playwright install chromium
```

### MCP Server (for Claude / Cursor)

```bash
bfs-mcp
```

No config needed — runs on stdio. Add to Claude Desktop (`claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "bfs-browser": {
      "command": "bfs-mcp"
    }
  }
}
```

Or Cursor (Settings → MCP → Add):

```json
{
  "mcpServers": {
    "bfs-browser": {
      "command": "bfs-mcp"
    }
  }
}
```

The agent will see 17 tools and a detailed instruction about the Betfunsports system. See [`skill.md`](skill.md) for the full skill description.

### Telegram Bot

```bash
pip install "bfs-mcp[bot]"
playwright install chromium

export BFS_TG_TOKEN=your_telegram_bot_token
export BFS_LLM_KEY=your_openrouter_key
export BFS_LLM_MODEL=deepseek/deepseek-chat   # ~$0.0002/request

bfs-bot
```

Write to the bot in natural language:
- "Залогинься как user@mail.com password123"
- "Какие купоны есть в футболе?"
- "Поставь на победу хозяев на Wooden столе"
- "Покажи баланс"

## Architecture

```
src/bfs_mcp/
├── browser.py   ← shared core: Playwright, auth, betting, DOM (~190 lines)
├── server.py    ← MCP server: 17 tools, stdio (~140 lines)
└── bot.py       ← Telegram bot: LLM agent, independent (~190 lines)
```

Both `server.py` and `bot.py` import `BFSBrowser` from `browser.py`. No code duplication.

## How Betfunsports works

P2P sports prediction platform. Player bets form a prize pool that is **fully distributed** among winners.

- **50% of bets win** (ranked by forecast accuracy, 0-100 points)
- Winnings proportional to **accuracy × bet size**
- Minimum winning coefficient: **1.3**

### Rooms

| Room | Currency | Range | Fee |
|------|----------|-------|-----|
| Wooden | BFS (virtual, free) | 1-10 | 0% |
| Bronze | EUR | 1-5 | 10% |
| Silver | EUR | 10-50 | 7.5% |
| Golden | EUR | 100-500 | 5% |

### Betting flow

1. Pick a sport & coupon (e.g. Football → 1X2)
2. Make a forecast (predict match outcomes)
3. Choose a room & stake
4. Wait for results — accuracy is scored 0-100, top 50% win

## Tools (17)

### BFS domain
| Tool | Description |
|------|-------------|
| `bfs_login` | Login (handles anti-bot honeypot) |
| `bfs_logout` | Logout |
| `bfs_state` | Auth status, username, EUR/BFS balance |
| `bfs_list_sports` | All available sports/coupons |
| `bfs_bet_info` | Parse coupon → events, outcomes, rooms |
| `bfs_place_bet` | Select outcomes, set stake, submit |

### Browser generic
| Tool | Description |
|------|-------------|
| `browser_navigate` | Go to URL |
| `browser_text` | Extract text by selector |
| `browser_html` | Get HTML |
| `browser_click` | Click element |
| `browser_fill` | Fill form field |
| `browser_select` | Select dropdown |
| `browser_screenshot` | PNG screenshot |
| `browser_eval` | Execute JavaScript |
| `browser_forms` | List all forms |
| `browser_links` | List links |
| `browser_wait` | Wait ms |

## Env vars (bot only)

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `BFS_TG_TOKEN` | yes | — | Telegram bot token |
| `BFS_LLM_KEY` | yes | — | OpenRouter / OpenAI API key |
| `BFS_LLM_BASE` | no | `https://openrouter.ai/api/v1` | LLM API base URL |
| `BFS_LLM_MODEL` | no | `deepseek/deepseek-chat` | Model ID |
| `BFS_MAX_HISTORY` | no | `30` | Conversation memory |
| `BFS_MAX_ITER` | no | `8` | Max tool-call iterations |
