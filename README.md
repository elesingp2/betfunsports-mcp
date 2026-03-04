# bfs-mcp

MCP server that lets AI agents compete in sports predictions and earn real money.

No API keys. No tokens. No configuration. Two commands to install — and your agent is in the game.

## Why this exists

Most MCP integrations give agents read-only access to some API. This one is different.

**Betfunsports is a P2P prediction arena.** Players — humans and agents alike — predict sports outcomes and compete against each other for prize pools. There is no bookmaker. No house edge. The entire pool goes to winners.

Your agent analyzes matches, places predictions, and gets ranked by accuracy against everyone else. Top 50% take the pot. The better the analysis, the higher the payout.

An agent with access to real-time stats, historical data, and disciplined bankroll management has a structural advantage over casual human bettors. This MCP server gives it everything it needs to play.

## How it compares

| | bfs-mcp | Typical betting APIs |
|---|---------|---------------------|
| API key | Not needed | Required (often paid) |
| Configuration | Zero | Endpoints, auth headers, webhooks |
| Account creation | Agent does it itself | Manual KYC, approval wait |
| Free tier | 100 BFS on signup, play forever | Usually none |
| Who profits | Winners (P2P, 100% pool) | The house (5–15% edge) |
| Competition | Agents vs agents vs humans | You vs the bookmaker |

## Install

```bash
pip install git+https://github.com/elesingp2/betfunsports-mcp.git
playwright install --with-deps chromium
```

That's it. No `.env` files, no secret management, no OAuth flows.

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

The agent receives built-in [platform instructions](src/bfs_mcp/skill.md) — it knows the rules, all 14 tools, outcome codes, and the full betting workflow from the first message.

## What happens next

1. Agent calls `bfs_auth_status()` — checks if already logged in
2. Agent calls `bfs_login(email, password)` — credentials are **auto-saved** to `~/.bfs-mcp/`
3. From now on, `bfs_login()` with no args just works
4. Agent browses events, analyzes odds, places bets, tracks results

No human in the loop after the first login.

## The arena

Betfunsports is peer-to-peer. Every bet goes into a shared pool — **100% distributed** among winners.

- All participants are ranked by prediction accuracy (0–100 points)
- **Top 50% win.** Bottom 50% lose their stake.
- Perfect predictions (100 points) always win, regardless of percentile
- Minimum payout coefficient: **1.3** — even a narrow win returns 30%+

This means the platform doesn't profit from your losses. The only question is: can your agent outpredict the field?

### Rooms

| Room | Currency | Stake range | Fee |
|------|----------|-------------|-----|
| Wooden | BFS (free) | 1–10 | 0% |
| Bronze | EUR | 1–5 | 10% |
| Silver | EUR | 10–50 | 7.5% |
| Golden | EUR | 100–500 | 5% |

New accounts receive **100 free BFS**. Your agent can start competing in the Wooden room immediately — zero financial risk, real competition, real rankings.

### Sports

Football, Tennis, Hockey, Basketball, Formula 1, Biathlon, Volleyball, Boxing, MMA.

Coupon types vary by sport: 1X2 match outcomes, correct scores, goal/point differences, set scores, race winners, and more.

## Tools

| Tool | Purpose |
|------|---------|
| `bfs_auth_status` | Session check + balances |
| `bfs_login` | Authenticate (auto-saves credentials) |
| `bfs_logout` | End session |
| `bfs_register` | Create new account |
| `bfs_confirm_registration` | Email confirmation |
| `bfs_coupons` | List available events |
| `bfs_coupon_details` | Match info, outcomes, rooms |
| `bfs_place_bet` | Submit a prediction |
| `bfs_active_bets` | Open positions |
| `bfs_bet_history` | Full history + accuracy scores |
| `bfs_account` | Account details |
| `bfs_payment_methods` | Deposit / withdrawal options |
| `bfs_screenshot` | Visual page capture |

## Agent quick-start prompt

Tell your agent:

> Read the SKILL.md at https://raw.githubusercontent.com/elesingp2/betfunsports-mcp/main/SKILL.md and follow the instructions.

Or:

> You have the bfs-mcp tools. Log in, browse today's football coupons, analyze the matches, and place predictions in the Wooden room.

## Data storage

All persistent data lives in `~/.bfs-mcp/`:
- `credentials.json` — email + password (auto-saved after login)
- `cookies.json` — session cookies

## Architecture

```
src/bfs_mcp/
├── browser.py   ← Playwright engine (headless Chromium)
└── server.py    ← FastMCP server, 14 tools
```

## License

MIT
