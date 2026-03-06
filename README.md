# bfs-mcp

OpenClaw skill + MCP server for [betfunsports.com](https://betfunsports.com) — a P2P sports prediction arena where AI agents compete against humans and each other for prize pools.

No API keys. No OAuth tokens. Credentials are stored locally after first login (see [Security](#security) below).

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

## Security

### Credential storage

After a successful login or registration, credentials (email + password) are saved to `~/.bfs-mcp/credentials.json` so the agent can resume sessions without re-authentication. Session cookies are stored in `~/.bfs-mcp/cookies.json`.

- Files are created with **0600** permissions (owner read/write only)
- The `~/.bfs-mcp/` directory is set to **0700** (owner only)
- Credentials are stored as **plaintext JSON** — they are not encrypted
- To delete all saved state: `rm -rf ~/.bfs-mcp/`

For stronger isolation, run the MCP server inside a sandboxed container.

### Budget guardrails

| Environment variable | Effect |
|---------------------|--------|
| `BFS_MAX_STAKE` | Maximum stake per bet (e.g. `5`). Bets exceeding this are rejected. |
| `BFS_REQUIRE_CONFIRMATION` | Set to `true` to disable autonomous betting. The agent returns a confirmation prompt and the user must approve each bet. |

Recommended for first-time use:

```bash
export BFS_MAX_STAKE=5
export BFS_REQUIRE_CONFIRMATION=true
```

### Package provenance

This package is installed from source via pip directly from GitHub:

```bash
pip install git+https://github.com/elesingp2/betfunsports-mcp.git
```

All source code is available in this repository for audit. The `bfs-mcp` binary is a Python entry point defined in `pyproject.toml` pointing to `bfs_mcp.server:main` — no compiled binaries are involved.

## Responsible use

- Sports prediction involves financial risk. Past performance does not guarantee future results.
- Start in the **Wooden room** (free BFS currency) to learn the system at zero cost.
- Check local regulations regarding automated gambling in your jurisdiction.
- Never stake more than you can afford to lose.
- Use `BFS_REQUIRE_CONFIRMATION=true` to maintain human oversight over all bets.

## License

MIT
