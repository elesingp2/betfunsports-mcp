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

Betfunsports is peer-to-peer. Every bet goes into a shared pool — **100% distributed** among winners.

- All participants are ranked by prediction accuracy (0–100 points)
- **Top 50% win.** Bottom 50% lose their stake.
- Perfect predictions (100 points) always win, regardless of percentile
- Minimum payout coefficient: **1.3** — even a narrow win returns 30%+

The agent analyzes matches, places predictions, tracks accuracy, and refines strategy — fully autonomously after initial login.

New accounts receive **100 free BFS** — zero-risk competition from the start.

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

## Responsible use

- Sports prediction involves financial risk. Past performance does not guarantee future results.
- Start in the **Wooden room** (free BFS currency) to learn the system at zero cost.
- Check local regulations regarding automated gambling in your jurisdiction.
- Never stake more than you can afford to lose.

## License

MIT
