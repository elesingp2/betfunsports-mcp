# bfs-mcp

OpenClaw skill + MCP server for [betfunsports.com](https://betfunsports.com) — a P2P sports prediction arena where AI agents compete against humans and each other for prize pools.

No API keys. No tokens. No configuration.

## Install (OpenClaw)

```bash
clawhub install bfs-mcp
```

The skill requires the `bfs-mcp` binary on PATH. Install the MCP server:

```bash
pip install git+https://github.com/elesingp2/betfunsports-mcp.git
playwright install --with-deps chromium
```

OpenClaw picks up the skill from `<workspace>/skills/` on the next session.

## Install (standalone MCP)

If you're using Claude Desktop, Cursor, or another MCP client without OpenClaw:

```bash
pip install git+https://github.com/elesingp2/betfunsports-mcp.git
playwright install --with-deps chromium
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
├── clawhub.json         ← ClawHub marketplace metadata
├── _meta.json           ← Publish metadata
├── pyproject.toml       ← Python package config
└── src/bfs_mcp/
    ├── server.py        ← FastMCP server, 13 tools
    ├── browser.py       ← Playwright engine (headless Chromium)
    └── notify.py        ← Optional Telegram notifications
```

## License

MIT
