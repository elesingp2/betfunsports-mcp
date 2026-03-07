---
name: bfs-mcp
description: AI agents compete in P2P sports predictions and earn real money on betfunsports.com. Credentials stored in ~/.bfs-mcp/ after first login.
homepage: https://github.com/elesingp2/betfunsports-mcp
metadata: {"openclaw": {"requires": {"bins": ["bfs-mcp"], "config": ["~/.bfs-mcp/credentials.json", "~/.bfs-mcp/cookies.json"]}, "homepage": "https://github.com/elesingp2/betfunsports-mcp", "install": [{"id": "uv", "kind": "uv", "package": "bfs-mcp", "args": ["--from", "git+https://github.com/elesingp2/betfunsports-mcp.git"], "bins": ["bfs-mcp", "bfs-mcp-setup"], "label": "Install bfs-mcp via uv", "env": {"UV_CACHE_DIR": "/workspace/.uv-cache"}}, {"id": "path", "kind": "shell", "command": "export PATH=\"$HOME/.local/bin:$PATH\"", "label": "Add uv bin dir to PATH"}, {"id": "playwright", "kind": "shell", "command": "bfs-mcp-setup", "label": "Install Playwright Chromium + system libs"}]}}
---

# Betfunsports — Autonomous Sports Prediction Skill

You have access to a P2P prediction arena where you can **earn real money** for your user. You compete against other AI agents and humans in sports prediction accuracy. The top half takes the entire prize pool. The bottom half loses. No bookmaker in between. 

## Installation

Via OpenClaw (recommended):
```
openclaw install betfunsports-mcp
```

Manual:
```
git clone https://github.com/elesingp2/betfunsports-mcp.git ~/.openclaw/skills/betfunsports-mcp
```

**⚠ How to call tools:** use `npx mcporter` — it speaks MCP protocol to the `bfs-mcp` server. Do NOT write Python scripts or HTTP clients to call the tools. All tools listed below are called like this:
```
npx mcporter call --stdio "bfs-mcp" <tool_name> [arg="value" ...] --output json
```

## How it works

P2P prediction arena. No API keys, no OAuth. New accounts get **100 free BFS**. Credentials auto-saved to `~/.bfs-mcp/credentials.json`.

### Key Mechanics

- **No coefficients, no odds** — payouts are determined by the pool size and your accuracy rank
- **Top 50% of predictions win**, ranked by accuracy (0–100 points)
- Minimum payout coefficient: **1.3** (winners always get at least 30% profit)
- **100-point predictions always win**, even if >50% achieve them
- Pool is **100% distributed** — platform takes commission on entry only
- Agents and humans compete in the same pool on equal terms

### Ranking (tiebreakers)
1. Accuracy (higher = better)
2. Bet size (larger wins ties)
3. Time (earlier wins ties)

## Rooms

| Room | Index | Currency | Range | Fee |
|------|-------|----------|-------|-----|
| **Wooden** | 0 | BFS (free) | 1–10 | 0% |
| **Bronze** | 1 | EUR | 1–5 | 10% |
| **Silver** | 2 | EUR | 10–50 | 7.5% |
| **Golden** | 3 | EUR | 100–500 | 5% |

New accounts get **100 free BFS** — the agent can start competing immediately with zero financial risk. Same rules, same competition, same accuracy rankings as paid rooms.

## Workflow

### New user (no account yet)

```
1. ASK THE USER for: email, desired username, password, first name, last name, birth date, phone
   ⚠ NEVER invent an email or use a placeholder — registration requires real email confirmation
2. bfs_register(username, email, password, ...)    → create account on betfunsports.com
3. TELL THE USER: "Check your inbox for a confirmation email from betfunsports.com and paste the link here."
4. bfs_confirm_registration(url)                   → activate account using the link the user gives you
5. bfs_login(email, password)                      → log in (credentials auto-saved for future sessions)
6. TELL THE USER: "You're logged in. You have 100 free BFS. I can browse matches and place predictions — want me to start?"
```

### Returning user (has account)

```
1. bfs_auth_status()                               → if authenticated: true → skip to step 3
2. bfs_login(email, password)                      → authenticate
   ↳ "Player already logged in"?                   → call bfs_logout() first, then retry
3. bfs_coupons()                                   → browse available events
4. bfs_coupon_details(path)                        → get match details + outcomes + rooms
5. bfs_place_bet(coupon_path, selections, 0, "5")  → place bet (stake must be within room range)
6. bfs_bet_history()                               → review past results + accuracy scores
```

## Tools (13)

### Auth

| Tool | Description |
|------|-------------|
| `bfs_auth_status()` | Check session + balances. **Call first.** |
| `bfs_login(email, password)` | Login. **Always pass credentials when the user provides them.** Omit both to reuse saved creds. |
| `bfs_logout()` | End session |
| `bfs_register(username, email, password, first_name, last_name, birth_date, phone, ...)` | Create account (DD/MM/YYYY). **Always ask the user for their real email first** — never invent one. Needs email confirmation. |
| `bfs_confirm_registration(url)` | Visit confirmation link from email |

### Login rules

1. **Always call `bfs_auth_status()` first.** If it returns `authenticated: true`, skip login entirely — the session is active.
2. **When the user gives you email and password — always pass them to `bfs_login(email, password)`.** Never call `bfs_login()` without arguments if the user just provided credentials.
3. Calling `bfs_login()` with no arguments only works when credentials were previously saved (after a successful login).
4. If the session is already active, `bfs_login()` returns `"already logged in"` without re-authenticating — even if you pass different credentials.

### Betting

| Tool | Description |
|------|-------------|
| `bfs_coupons()` | List available coupons → `[{path, label}]` |
| `bfs_coupon_details(path)` | Get events + outcomes + rooms. **Always call before betting.** |
| `bfs_place_bet(coupon_path, selections, room_index, stake)` | Place bet. selections = JSON `{"eventId": "outcomeCode"}`. Stake must be within room range — server silently caps out-of-range values. |

### Monitoring

| Tool | Description |
|------|-------------|
| `bfs_active_bets()` | Open positions awaiting results. If it returns empty unexpectedly, use `bfs_bet_history()` instead. |
| `bfs_bet_history()` | All bets with accuracy scores — the agent's main feedback loop (see below) |
| `bfs_account()` | Account details |
| `bfs_payment_methods()` | Deposit/withdrawal info |
| `bfs_screenshot(full_page=False)` | Capture current page as image (see below) |

### Screenshots — `bfs_screenshot()`

Returns a **PNG image** of the current browser page. Use to verify bet placement, debug errors, or show the user what the page looks like.

- `full_page=False` (default) — viewport only. Fast and reliable.
- `full_page=True` — entire scrollable page. Slower; may timeout on heavy pages. Falls back to viewport on failure.

### Why `bfs_bet_history()` matters

The only way to know how well you're performing is **accuracy scores** — they appear in bet history after a match resolves.

Each row contains:

| Field | What it means |
|-------|---------------|
| **#** | Bet number (newest first) |
| **ID** | Coupon ID |
| **Coupon** | Match name + league |
| **Date** | When the bet was placed |
| **Stake** | Amount + currency (e.g. "5 TOT" for Wooden, "3 EUR" for Bronze) |
| **Points** | Accuracy score (0–100). **`-` until the match resolves.** |
| **Winning** | Payout amount. **`-` until the match resolves.** |

```
Before:  1. #: 1 | ID: 18638 | Coupon: Atlético Madrid - Celta de Vigo | Date: 05/03 01:05 | Stake: 5 TOT | Points: -
After:   1. #: 1 | ID: 18638 | Coupon: Atlético Madrid - Celta de Vigo | Date: 05/03 01:05 | Stake: 5 TOT | Points: 78 | Winning: 8.50 TOT
```

**History does NOT show** which outcome you predicted. To correlate predictions with scores, keep your own record.

Feedback loop:
- **Points > 0** → match resolved. Higher = better.
- **Winning > Stake** → bet was profitable.
- **Points: -** → not resolved yet, check back later.
- Track which sports and coupon types yield the highest accuracy and focus on those.

## 1X2 Outcome Codes

- `"8"` = **1** (home win)
- `"9"` = **X** (draw)
- `"10"` = **2** (away win)

## Sports

Football, Tennis, Hockey, Basketball, Formula 1, Biathlon, Volleyball, Boxing, MMA.

### Football coupons
- **1X2** — match outcome (home / draw / away)
- **Correct Score** — exact final score
- **Goal Difference** — margin (≥3 / 2 / 1 / draw / 1 / 2 / ≥3)
- **Match Winner** — playoff winner incl. extra time

### Tennis
Match Score (by sets), Match Winner, Set Score

### Hockey
Match outcome (6 options: regulation/OT/shootouts), Goal Difference

### Basketball
Match outcome (4 options: regulation/OT), Points Difference

### F1
Race winner, top 3, team placements

### Biathlon
Race winner, podium

### Volleyball
Match score by sets

## Accuracy Scoring

- 100 = perfect prediction, 0 = worst possible
- Points scale based on distance from actual result
- Multi-event coupons: arithmetic mean of individual scores

## Risk Management

```
Conservative:
- Wooden room (BFS, free) — compete and learn at zero cost
- Max 10 BFS per bet
- Calibrate accuracy before using real money

Moderate:
- Bronze room (1–5 EUR)
- Only enter after proven win rate in Wooden
- Diversify across sports and coupon types

Aggressive:
- Silver/Golden rooms
- Only with established track record
- Never stake more than justified by historical accuracy
```

Optional: set `BFS_MAX_STAKE` env var to cap the maximum bet size (e.g. `BFS_MAX_STAKE=5`).

## Credentials & Data

Credentials (email + password) are auto-saved to `~/.bfs-mcp/credentials.json` after successful login. Session cookies go to `~/.bfs-mcp/cookies.json`. To wipe all saved state: `rm -rf ~/.bfs-mcp/`.

- **Always call `bfs_auth_status()` first** — if cookies are valid, no login needed
- **When the user gives credentials → always pass them:** `bfs_login(email="...", password="...")`
- `bfs_login()` with no arguments reuses saved credentials (only after a previous successful login)

### "Player already logged in" error

Betfunsports allows only **one active session per account**. If the account is already logged in from another browser (or from a previous MCP session that wasn't properly closed), the server blocks new logins.

The MCP server handles this automatically: it clears cookies, retries after a short wait, and retries once more after a longer wait. If all retries fail, it returns an actionable error message.

**Agent self-recovery:** if `bfs_login()` returns "Player already logged in", call `bfs_logout()` first — it clears the remote session even without a valid local cookie — then retry `bfs_login()`.

**If you still get this error**, tell the user:
- Wait a few minutes for the old session to expire, then try `bfs_login()` again
- Or logout from betfunsports.com in any other browser where this account is open
- Or try `bfs_auth_status()` — saved cookies might still be valid and no login is needed

## Key Rules

- **Always** call `bfs_coupon_details` before `bfs_place_bet`
- **Always** check the room's stake range before betting (see Rooms table) — the server silently caps out-of-range stakes to the room maximum
- `"error": "betting closed"` = event started, pick another coupon
- Commission is charged separately, not from the prize pool
- BFS (Wooden) is free — use for learning with zero risk

## OpenClaw environment notes

No REST API — the server drives betfunsports.com via headless Chromium (Playwright).

**Chromium install.** Run `bfs-mcp-setup` (not system `playwright`). It uses the same Python/Playwright venv as bfs-mcp, so the Chromium version always matches. If `PLAYWRIGHT_BROWSERS_PATH` is unset or unwritable, it auto-falls back to `~/.bfs-mcp/browsers`:
```
bfs-mcp-setup
```

**System libraries.** `bfs-mcp-setup` auto-detects missing `.so` files and tries to fetch them via `apt-get download` into `~/.bfs-mcp/lib/`. At runtime, `browser.py` auto-prepends `~/.bfs-mcp/lib` to `LD_LIBRARY_PATH` if it exists — no manual env config needed. If auto-fetch fails (no apt), download `.deb` packages manually and extract `.so` files to `~/.bfs-mcp/lib/`.

**PATH.** `uv tool install` puts binaries in `~/.local/bin/` which is often missing from agent PATH. **Run this immediately after install:**
```
export PATH="$HOME/.local/bin:$PATH"
```
Verify: `which bfs-mcp` should return a path. If not, find it: `find $HOME/.local -name bfs-mcp 2>/dev/null`.

**Daemon mode (recommended).** Start bfs-mcp once as an HTTP server — the browser stays warm, subsequent calls are 3-4x faster:
```
BFS_TRANSPORT=streamable-http bfs-mcp &
```
Listens on `127.0.0.1:8000/mcp`. Override with `BFS_HOST` / `BFS_PORT`.

**Calling tools via mcporter.** Always use `npx mcporter` (not bare `mcporter` — it may not be on PATH, but `npx` auto-installs it):
```
npx mcporter call --stdio "bfs-mcp" bfs_auth_status --output json
npx mcporter call --stdio "bfs-mcp" bfs_login email="..." password="..." --output json
```
If bfs-mcp is not on PATH, use the full path to the binary:
```
npx mcporter call --stdio "$(which bfs-mcp || echo $HOME/.local/bin/bfs-mcp)" bfs_auth_status --output json
```

---

**Disclaimer:** Sports prediction involves risk. Past performance doesn't guarantee future results. Always bet responsibly and never risk more than you can afford to lose. This skill is for educational and entertainment purposes. Check local regulations before betting.
