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
export UV_CACHE_DIR=/workspace/.uv-cache
export PLAYWRIGHT_BROWSERS_PATH=/workspace/playwright-browsers

uv tool install "bfs-mcp @ git+https://github.com/elesingp2/betfunsports-mcp.git"
playwright install chromium
```

Or use the bundled install script that handles environment setup automatically:

```bash
./install.sh
```

Or via pip:

```bash
export PLAYWRIGHT_BROWSERS_PATH=/workspace/playwright-browsers
pip install git+https://github.com/elesingp2/betfunsports-mcp.git
playwright install chromium
```

**Important:** After installing, make sure `~/.local/bin` is on your `PATH`:

```bash
export PATH="$HOME/.local/bin:$PATH"
```

OpenClaw picks up the skill from `<workspace>/skills/` on the next session.

When registering the MCP server in your client config, include the environment variables:

```json
{
  "mcpServers": {
    "bfs": {
      "command": "bfs-mcp",
      "env": {
        "PLAYWRIGHT_BROWSERS_PATH": "/workspace/playwright-browsers"
      }
    }
  }
}
```

## Install (standalone MCP)

If you're using Claude Desktop, Cursor, or another MCP client without OpenClaw:

```bash
export PLAYWRIGHT_BROWSERS_PATH=/workspace/playwright-browsers
uv tool install "bfs-mcp @ git+https://github.com/elesingp2/betfunsports-mcp.git"
playwright install chromium
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
├── install.sh           ← Install script (handles env setup automatically)
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

### `uv tool install` fails with "Permission denied" on cache

The `uv` cache directory (e.g. `/tmp/.tool-cache/uv/`) may be owned by a different user. Set `UV_CACHE_DIR` to a writable path before installing:

```bash
export UV_CACHE_DIR=/workspace/.uv-cache
uv tool install "bfs-mcp @ git+https://github.com/elesingp2/betfunsports-mcp.git"
```

### Chromium won't start — missing system libraries

Playwright's Chromium requires system libraries (`libnspr4`, `libnss3`, `libatk-bridge-2.0`, `libgbm1`, `libxkbcommon`, `libasound2`, `libdrm2`, `libwayland-server0`, etc.). If you have `sudo`:

```bash
playwright install-deps chromium
```

Without `sudo`, download the required `.deb` packages from a Debian mirror, extract the `.so` files, and set `LD_LIBRARY_PATH`:

```bash
mkdir -p /workspace/debs && cd /workspace/debs
# Download and extract packages (example for Debian bookworm, amd64):
apt-get download libnspr4 libnss3 libatk-bridge2.0-0 libgbm1 libxkbcommon0 libasound2 libdrm2
for f in *.deb; do dpkg-deb -x "$f" extracted; done
export LD_LIBRARY_PATH=/workspace/debs/extracted/usr/lib/x86_64-linux-gnu
```

Then include `LD_LIBRARY_PATH` in your MCP server config's `env` section.

### `PLAYWRIGHT_BROWSERS_PATH` points to unwritable location

Some environments pre-set `PLAYWRIGHT_BROWSERS_PATH` to a system path like `/opt/playwright-browsers`. Override it:

```bash
export PLAYWRIGHT_BROWSERS_PATH=/workspace/playwright-browsers
playwright install chromium
```

Include this variable in your MCP server config so the runtime can find the browser.

### `bfs-mcp` command not found after install

`uv tool install` places binaries in `~/.local/bin/`, which may not be on your `PATH`:

```bash
export PATH="$HOME/.local/bin:$PATH"
```

Add this to `~/.bashrc` to make it permanent.

## Responsible use

- Sports prediction involves financial risk. Past performance does not guarantee future results.
- Start in the **Wooden room** (free BFS currency) to learn the system at zero cost.
- Check local regulations regarding automated gambling in your jurisdiction.
- Never stake more than you can afford to lose.

## License

MIT
