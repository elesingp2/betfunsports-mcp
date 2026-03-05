# bfs-mcp

MCP server for [betfunsports.com](https://betfunsports.com) — lets AI agents compete in P2P sports predictions.

No API keys, no tokens, no config. Two commands to install.

## How it works

Betfunsports is a **peer-to-peer prediction arena**. Players predict sports outcomes, stakes go into a shared pool, and the top 50% by accuracy take everything. No bookmaker, no house edge. New accounts get **100 free BFS** to start at zero risk.

## Install

```bash
pip install git+https://github.com/elesingp2/betfunsports-mcp.git
playwright install --with-deps chromium
```

## Connect

**Claude Code:**
```bash
claude mcp add --transport stdio bfs -- bfs-mcp
```

**Claude Desktop** — add to `claude_desktop_config.json`:
```json
{ "mcpServers": { "bfs": { "command": "bfs-mcp" } } }
```

**Cursor:** Settings → MCP → Add → command: `bfs-mcp`

**OpenClaw:** install from [ClawHub](https://clawhub.ai) or add manually via stdio.

## Registration

The agent can register you via `bfs_register`. Just tell it your username, email, password, name, birth date, phone, and country. After registration, confirm your email by clicking the link.

**Password must** include upper + lower + digits + at least one symbol (`!@#$%`).

## Rooms

| Room | Currency | Stake | Fee |
|------|----------|-------|-----|
| Wooden | BFS (free) | 1–10 | 0% |
| Bronze | EUR | 1–5 | 10% |
| Silver | EUR | 10–50 | 7.5% |
| Golden | EUR | 100–500 | 5% |

## Tools (14)

| Tool | Purpose |
|------|---------|
| `bfs_auth_status` | Session check + balances |
| `bfs_login` | Authenticate |
| `bfs_logout` | End session |
| `bfs_register` | Create account |
| `bfs_confirm_registration` | Email confirmation |
| `bfs_coupons` | List events |
| `bfs_coupon_details` | Match info, outcomes, rooms |
| `bfs_place_bet` | Submit prediction |
| `bfs_active_bets` | Open positions |
| `bfs_bet_history` | History + accuracy scores |
| `bfs_account` | Account details |
| `bfs_payment_methods` | Deposit / withdrawal |
| `bfs_screenshot` | Page capture |

## Quick start

Tell your agent:

> Log in, browse today's football coupons, analyze the matches, and place predictions in the Wooden room.

## Telegram bot (optional)

Real-time notifications about agent activity — bets, results, balances.

```bash
pip install git+https://github.com/elesingp2/betfunsports-telegram-bot.git
export BFS_TG_TOKEN=your_bot_token      # @BotFather
export BFS_LLM_KEY=your_api_key         # openrouter.ai
bfs-bot
```

## Data

Saved to `~/.bfs-mcp/`: `credentials.json` (auto-saved) and `cookies.json`.

## License

MIT
