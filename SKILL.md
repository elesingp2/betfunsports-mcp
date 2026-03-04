---
name: betfunsports
description: Sports prediction MCP server for betfunsports.com. Browse events, place bets, track positions, and earn from sports predictions. Zero config — no API keys, no tokens needed.
homepage: https://betfunsports.com
metadata: {"emoji":"⚽","requires":{"bins":["pip","python3","playwright"]}}
---

# Betfunsports — Sports Prediction Skill

Trade sports predictions and profit from your knowledge directly from any MCP-compatible AI agent.

## Overview

This skill gives your AI agent full access to [betfunsports.com](https://betfunsports.com) — a P2P sports prediction platform:

- Browse upcoming sports events
- Analyze match details and outcomes
- Place bets across multiple rooms
- Track active bets and history
- Manage account and balances

**Zero configuration. No API keys. No tokens.** Credentials are auto-saved after first login.

## Installation

### 1. Install the MCP server

```bash
pip install git+https://github.com/elesingp2/betfunsports-mcp.git
playwright install --with-deps chromium
```

### 2. Connect to your MCP client

**Claude Desktop** — add to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "bfs": { "command": "bfs-mcp" }
  }
}
```

**Cursor** — Settings → MCP → Add → command: `bfs-mcp`

**Any MCP client** — run `bfs-mcp` on stdio.

That's it. The agent receives full platform instructions automatically.

## What is Betfunsports?

Betfunsports is a P2P sports prediction platform. Players' bets form a prize pool that is **fully distributed** among winners. No house edge.

```
Example: Football match — Real Madrid vs Barcelona

You predict: Real Madrid wins (1X2 → "1")
Stake: 5 BFS in Wooden room (free)

If your prediction accuracy ranks in top 50%:
- You win proportionally to accuracy × stake
- Minimum coefficient: 1.3 (you always get at least 30% profit)

If your prediction is in bottom 50%:
- You lose your stake
```

### Key Mechanics

- **Top 50% of predictions win**, ranked by accuracy (0–100 points)
- Winnings = accuracy × bet size (minimum coefficient **1.3**)
- **100-point predictions always win**, even if >50% achieve them
- Pool is **100% distributed** — platform takes commission on entry only

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

New accounts get **100 free BFS** — start betting immediately with zero risk in the Wooden room.

## Workflow

```
1. bfs_auth_status()                               → check session (often no login needed)
2. bfs_login(email, password)                      → authenticate (credentials auto-saved)
3. bfs_coupons()                                   → browse available events
4. bfs_coupon_details("/FOOTBALL/.../18638")       → get match details + outcomes
5. bfs_place_bet(coupon_path, selections, 0, "5")  → place bet
6. bfs_active_bets()                               → track open positions
7. bfs_bet_history()                               → review past results
```

## Tools (14)

### Auth

| Tool | Description |
|------|-------------|
| `bfs_auth_status()` | Check session + balances. **Call first.** |
| `bfs_login(email, password)` | Login. Empty = use saved creds. Auto-saves on success. |
| `bfs_logout()` | End session |
| `bfs_register(username, email, password, first_name, last_name, birth_date, phone, ...)` | Create account (DD/MM/YYYY). Needs email confirmation. |
| `bfs_confirm_registration(url)` | Visit confirmation link from email |

### Betting

| Tool | Description |
|------|-------------|
| `bfs_coupons()` | List available coupons → `[{path, label}]` |
| `bfs_coupon_details(path)` | Get events + outcomes + rooms. **Always call before betting.** |
| `bfs_place_bet(coupon_path, selections, room_index, stake)` | Place bet. selections = JSON `{"eventId": "outcomeCode"}` |

### Monitoring

| Tool | Description |
|------|-------------|
| `bfs_active_bets()` | Open positions awaiting results |
| `bfs_bet_history()` | Full history with accuracy scores |
| `bfs_account()` | Account details |
| `bfs_payment_methods()` | Deposit/withdrawal info |
| `bfs_screenshot()` | Current page screenshot |

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

## Betting Strategies

### Information Edge

```
Strategy: Bet on sports where you have knowledge

Examples:
- Follow specific leagues closely
- Track team form, injuries, suspensions
- Understand home/away dynamics
- React to late lineup changes

Process:
1. Find coupon where you have an edge
2. Assess if outcomes reflect reality
3. Pick the best room for your bankroll
4. Monitor results and adjust
```

### Wooden Room (Risk-Free Learning)

```
Strategy: Use free BFS to learn the platform

Benefits:
- 100 free BFS on signup
- 0% commission
- No real money at risk
- Same mechanics as paid rooms

Process:
1. Register and get 100 BFS
2. Place small bets (1-5 BFS) across different sports
3. Learn accuracy scoring patterns
4. Graduate to Bronze when consistent
```

### Multi-Event Coupons

```
Strategy: Bet on multiple events for higher potential returns

How it works:
- Accuracy = arithmetic mean of individual predictions
- More events = higher variance but potential for big wins

Tips:
- Stick to sports you know
- Mix "safe" picks with value bets
- Track which sports give you best accuracy
```

## Risk Management

```
Conservative:
- Stick to Wooden room (BFS, free)
- Max 10 BFS per bet
- Learn accuracy patterns first

Moderate:
- Bronze room (1-5 EUR)
- Track win rate before sizing up
- Diversify across sports

Aggressive:
- Silver/Golden rooms
- Only after proven track record
- Never bet more than you can afford to lose
```

## Credentials & Data

Credentials are **auto-saved** to `~/.bfs-mcp/credentials.json` after successful login or registration.

- `bfs_login()` with no arguments uses saved credentials
- `bfs_auth_status()` checks if the session is still alive (call first — often no login needed)
- First-time: pass email + password to `bfs_login(email, password)`, they are saved automatically

All persistent data is in `~/.bfs-mcp/`:
- `credentials.json` — email + password
- `cookies.json` — browser session cookies

## Key Rules

- **Always** call `bfs_coupon_details` before `bfs_place_bet`
- `"error": "betting closed"` = event started, pick another coupon
- Commission is charged separately, not from the prize pool
- BFS (Wooden) is free — use for learning with zero risk

## Why Betfunsports?

| Feature | Betfunsports | Traditional Bookmakers |
|---------|-------------|----------------------|
| House edge | None (P2P) | 5-15% |
| Prize pool | 100% distributed | House keeps margin |
| Free play | 100 BFS on signup | Rare/limited |
| AI-friendly | MCP server, zero config | No API / complex APIs |
| Transparency | Accuracy-based ranking | Opaque odds |

---

**Disclaimer:** Sports prediction involves risk. Past performance doesn't guarantee future results. Always bet responsibly and never risk more than you can afford to lose. This skill is for educational and entertainment purposes. Check local regulations before betting.
