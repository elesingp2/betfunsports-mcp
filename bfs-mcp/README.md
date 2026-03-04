# betfunsports-mcp

MCP server for [betfunsports.com](https://betfunsports.com) — zero-config sports prediction platform API for AI agents.

Install → connect → the agent can register, login, browse events, place bets, and earn.
No API keys. No configuration. No tokens. Credentials are auto-saved after first login.

## Quick Start (for AI agents)

Tell your agent:

> Read the SKILL.md at https://raw.githubusercontent.com/elesingp2/betfunsports-mcp/main/SKILL.md and follow the installation instructions.

Or just:

> Install betfunsports MCP from https://github.com/elesingp2/betfunsports-mcp — read SKILL.md and follow instructions.

## Install

```bash
pip install git+https://github.com/elesingp2/betfunsports-mcp.git
playwright install --with-deps chromium
```

## Connect

**Claude Desktop** (`claude_desktop_config.json`):
```json
{
  "mcpServers": {
    "bfs": { "command": "bfs-mcp" }
  }
}
```

**Cursor:** Settings → MCP → Add → command: `bfs-mcp`

**Any MCP client:** `bfs-mcp` runs on stdio.

The agent receives [`skill.md`](src/bfs_mcp/skill.md) as built-in instructions — it knows the platform, all tools, and the betting workflow automatically.

## What happens

1. Agent calls `bfs_auth_status()` — checks if already logged in
2. Agent calls `bfs_login("user@email.com", "password")` — authenticates, **credentials auto-saved** to `~/.bfs-mcp/`
3. Next session: `bfs_login()` with no args uses saved credentials
4. Agent browses coupons, places bets, analyzes history

No human in the loop after initial login.

## How Betfunsports works

P2P sports prediction. Bets form a prize pool — **100% distributed** among winners.

- Top 50% of bets win (ranked by accuracy 0–100)
- Perfect predictions (100 points) always win
- Min win coefficient: 1.3
- Sports: Football, Tennis, Hockey, Basketball, F1, Biathlon, Volleyball, Boxing, MMA

| Room | Currency | Range | Fee |
|------|----------|-------|-----|
| Wooden | BFS (free) | 1–10 | 0% |
| Bronze | EUR | 1–5 | 10% |
| Silver | EUR | 10–50 | 7.5% |
| Golden | EUR | 100–500 | 5% |

New accounts get **100 free BFS** — start betting immediately.

## Tools (14)

| Tool | What it does |
|------|-------------|
| `bfs_auth_status` | Check session + balances |
| `bfs_login` | Login (auto-saves creds) |
| `bfs_logout` | End session |
| `bfs_register` | Create account |
| `bfs_confirm_registration` | Email confirmation |
| `bfs_coupons` | List available events |
| `bfs_coupon_details` | Match details + outcomes |
| `bfs_place_bet` | Place a bet |
| `bfs_active_bets` | Open positions |
| `bfs_bet_history` | Full history |
| `bfs_account` | Account info |
| `bfs_payment_methods` | Deposit/withdrawal |
| `bfs_screenshot` | Page screenshot |

## Data storage

All persistent data is in `~/.bfs-mcp/`:
- `credentials.json` — email + password (auto-saved after login)
- `cookies.json` — browser session cookies

## Architecture

```
src/bfs_mcp/
├── browser.py   ← Playwright engine (headless Chromium)
└── server.py    ← MCP server, 14 tools
```

## License

MIT
