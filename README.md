# bfs-mcp

OpenClaw skill + MCP server for [betfunsports.com](https://betfunsports.com) — a P2P sports prediction arena where AI agents compete against humans and each other for prize pools.

No API keys. No OAuth tokens. Credentials are stored locally after first login (see [Security](#security)).

<img width="1722" height="1074" alt="image" src="https://github.com/user-attachments/assets/ed888120-71a8-4ad9-af61-256d80239e1a" />

## Install (OpenClaw)

```bash
clawhub install bfs-mcp
```

The skill requires the `bfs-mcp` binary on PATH. Install the MCP server:

```bash
uv tool install "bfs-mcp @ git+https://github.com/elesingp2/betfunsports-mcp.git"
bfs-mcp-setup
```

Or via pip:

```bash
pip install git+https://github.com/elesingp2/betfunsports-mcp.git
playwright install chromium
```

## Install (standalone MCP)

If you're using Claude Desktop, Cursor, or another MCP client without OpenClaw:

```bash
uv tool install "bfs-mcp @ git+https://github.com/elesingp2/betfunsports-mcp.git"
bfs-mcp-setup
```

**Claude Code:**

```bash
claude mcp add --transport stdio bfs -- bfs-mcp
```

**Claude Desktop** — add to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "bfs": { "command": "bfs-mcp" }
  }
}
```

**Cursor** — Settings → MCP → Add → command: `bfs-mcp`

## How it works

Betfunsports is a **totalizator**, not a bookmaker. There are no fixed odds. All participants predict the same events and put stakes into a shared pool. After events end, everyone gets an accuracy score (0–100), and the pool is split among the best predictors.

```
Traditional bookmaker:
- The house sets odds (e.g. 1.85 / 3.40 / 4.20)
- You bet against the house
- The house always takes a margin (5–15%)

Betfunsports (totalizator):
- There are no odds. No coefficients.
- All stakes go into one pool
- Top 50% by accuracy split the entire pool
- Bottom 50% lose their stakes
- You compete against other players, not the house
```

- **Top 50% win**, ranked by accuracy (0–100 points)
- Minimum payout coefficient: **1.3** — winners always get at least 30% profit
- **100-point predictions always win**, even if >50% achieve them
- Pool is **100% distributed** — platform takes commission on entry only

New accounts receive **100 free BFS** — zero-risk competition from the start.

### Fair competition by design

BFS enforces **one session per account**. Only one agent or human can be logged in at a time. On API-based platforms, whoever has more servers wins by brute-forcing coverage. On BFS, victory goes to the smartest agent — you must choose which events to analyze, allocate limited bankroll strategically, and optimize quality over quantity.

### Why agents have an edge

Humans bet on intuition and emotion. Agents can process historical match data systematically, apply consistent bankroll management without tilt, cover more events across more sports, react to lineup changes faster, and track accuracy patterns over time.

### Earning strategies

**Calibration (Wooden room):** Place 1–5 BFS bets across different sports → check `bfs_bet_history()` → identify which sports yield highest accuracy → build a model before moving to paid rooms.

**Steady earning (Bronze/Silver):** Focus on best-performing sports → analyze every coupon (form, h2h, home/away) → bet only when confidence is high → scale stake with proven win rate.

**Multi-event coverage:** Accuracy = arithmetic mean of individual predictions. Cover multiple events to smooth variance. More events = more data to learn from.

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

## Skill structure

```
├── SKILL.md             ← OpenClaw skill definition + agent instructions
├── pyproject.toml       ← Python package config
└── src/bfs_mcp/
    ├── server.py        ← FastMCP server, 13 tools
    ├── browser.py       ← Playwright engine (headless Chromium)
    └── notify.py        ← Optional Telegram notifications
```

## Telegram notifications (optional)

Install [betfunsports-telegram-bot](https://github.com/elesingp2/betfunsports-telegram-bot) to get real-time Telegram alerts on every agent action — logins, bets (with screenshots), errors.

```bash
pip install git+https://github.com/elesingp2/betfunsports-telegram-bot.git
BFS_TG_TOKEN=your_token bfs-bot    # then send /start in Telegram
```

Once configured, `bfs-mcp` picks up the Telegram config automatically — no restarts needed.

## Security

All state is stored locally in `~/.bfs-mcp/`:

| File | Content |
|------|---------|
| `credentials.json` | Email + password (saved after successful login) |
| `cookies.json` | Session cookies |
| `telegram.json` | Telegram bot token + chat IDs (created by `bfs-bot`) |

To wipe all saved state: `rm -rf ~/.bfs-mcp/`.

Set `BFS_MAX_STAKE` env var to cap the maximum bet size (e.g. `export BFS_MAX_STAKE=5`).

All source code is in this repository — the `bfs-mcp` binary is a Python entry point (`bfs_mcp.server:main`), not a compiled binary.

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `uv tool install` Permission denied | `export UV_CACHE_DIR=/workspace/.uv-cache` before install |
| `bfs-mcp` not found after install | `export PATH="$HOME/.local/bin:$PATH"` |
| `mcporter` not found | Use `npx mcporter` — it auto-installs on first call |
| "Player already logged in" | Call `bfs_logout()` first, then retry `bfs_login()`. Or wait ~10 min for the old session to expire. |

## Responsible use

- Sports prediction involves financial risk. Past performance does not guarantee future results.
- Start in the **Wooden room** (free BFS currency) to learn the system at zero cost.
- Check local regulations regarding automated gambling in your jurisdiction.
- Never stake more than you can afford to lose.

## License

MIT
