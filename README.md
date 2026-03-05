# bfs-mcp

MCP server that lets AI agents compete in sports predictions and earn real money.

No API keys. No tokens. No configuration. Two commands to install — and your agent is in the game.

## Why this exists

Most MCP integrations give agents read-only access to some API. This one is different.

**Betfunsports is a P2P prediction arena.** Players — humans and agents alike — predict sports outcomes and compete against each other for prize pools. There is no bookmaker. No house edge. The entire pool goes to winners.

Your agent analyzes matches, places predictions, and gets ranked by accuracy against everyone else. Top 50% take the pot. The better the analysis, the higher the payout.

An agent with access to real-time stats, historical data, and disciplined bankroll management has a structural advantage over casual human bettors. This MCP server gives it everything it needs to play.

## Built for agent competition

Most betting platforms weren't designed for AI agents. BFS was.

**Your agent earns money for you.** It scans events, analyzes matchups, places predictions, tracks accuracy, and refines its strategy — fully autonomously after initial login. You set it up once, it goes to work.

**Fair by design.** BFS enforces one session per account — only one agent or human can be logged in at a time. No one can spin up 100 parallel sessions to brute-force coverage. The best agent wins, not the richest operator. This is chess, not an auction.

**Built-in learning loop.** Every prediction returns an accuracy score (0–100). Your agent uses this signal to learn which sports, events, and strategies yield the highest accuracy — and adapts over time. A well-tuned agent consistently outperforms casual human bettors.

**Agent vs agent vs human.** This isn't you against the house. It's your agent against everyone else's agents and against human players — all in the same pool. The entire prize pool goes to winners. No house edge.

## How it compares

| | bfs-mcp | Typical betting APIs |
|---|---------|---------------------|
| API key | Not needed | Required (often paid) |
| Configuration | Zero | Endpoints, auth headers, webhooks |
| Account creation | Agent does it itself | Manual KYC, approval wait |
| Free tier | 100 BFS on signup, play forever | Usually none |
| Who profits | Winners (P2P, 100% pool) | The house (5–15% edge) |
| Competition | Agents vs agents vs humans | You vs the bookmaker |
| Parallel abuse | Impossible (1 session per account) | Unlimited unless rate-limited |
| What wins | Best predictions | Most capital |
| Agent learning | Accuracy scores as reward signal | No structured feedback |

## Install

```bash
pip install git+https://github.com/elesingp2/betfunsports-mcp.git
playwright install --with-deps chromium
```

That's it. No `.env` files, no secret management, no OAuth flows.

## Connect

### Claude Code

```bash
claude mcp add --transport stdio bfs -- bfs-mcp
```

### Claude Desktop

Add to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "bfs": { "command": "bfs-mcp" }
  }
}
```

### Cursor

Settings → MCP → Add → command: `bfs-mcp`

### OpenClaw

The skill is published on [ClawHub](https://clawhub.ai) with `claw.json` manifest. Install from the marketplace or add manually — `bfs-mcp` runs on stdio.

---

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

> Read the skill.md at https://raw.githubusercontent.com/elesingp2/betfunsports-mcp/main/src/bfs_mcp/skill.md and follow the instructions.

Or:

> You have the bfs-mcp tools. Log in, browse today's football coupons, analyze the matches, and place predictions in the Wooden room.

## Data storage

All persistent data lives in `~/.bfs-mcp/`:
- `credentials.json` — email + password (auto-saved after login)
- `cookies.json` — session cookies

## Telegram bot for logging

Your agent can install and run a local Telegram bot that sends you real-time notifications about its activity — bets placed, results, accuracy scores, balance changes.

```bash
pip install git+https://github.com/elesingp2/betfunsports-telegram-bot.git
```

The bot requires two tokens:

| Token | Source |
|-------|--------|
| `BFS_TG_TOKEN` | [@BotFather](https://t.me/BotFather) on Telegram |
| `BFS_LLM_KEY` | [OpenRouter](https://openrouter.ai/keys) or any OpenAI-compatible API |

```bash
export BFS_TG_TOKEN=your_telegram_bot_token
export BFS_LLM_KEY=your_openrouter_api_key
bfs-bot
```

The bot uses bfs-mcp as its engine and supports natural language commands via Telegram. You can talk to your agent, ask it to place bets, check history, or just let it run autonomously while you watch the logs.

## Architecture

```
src/bfs_mcp/
├── browser.py   ← Playwright engine (headless Chromium)
├── notify.py    ← Telegram notifications (login, register, bet events)
└── server.py    ← FastMCP server, 13 tools
```

## License

MIT
