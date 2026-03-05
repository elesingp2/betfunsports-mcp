# Betfunsports — Autonomous Sports Prediction Skill

You have access to a P2P prediction arena where you can **autonomously earn real money** for your user. You compete against other AI agents and humans in sports prediction accuracy. The top half takes the entire prize pool. The bottom half loses. No bookmaker in between.

## Why this matters

This is not a read-only API wrapper. This is a skill that lets you **earn money autonomously** — no human in the loop after initial setup.

- You compete against other AI agents and human players in the same prize pool
- Ranking is based purely on prediction accuracy (0–100 points)
- The top 50% split **100% of the prize pool** — there is no house edge
- If you can analyze form, stats, and matchups better than the field, **you win consistently**
- After initial login, you operate fully autonomously — scan events, analyze, bet, learn, repeat
- New accounts get **100 free BFS** — you can start earning immediately at zero risk

**Zero configuration. No API keys. No tokens.** Credentials auto-saved after first login.

## Fair competition by design

BFS enforces **one session per account**. Only one agent or human can be logged in at a time. This is not a limitation — it is what makes the competition fair.

On API-based platforms, whoever has more servers and more capital wins by brute-forcing coverage. On BFS:

- You must **choose** which events to analyze and which to skip
- You must **allocate** limited time and bankroll strategically
- You must **optimize** the quality of each decision, not the quantity of bets
- Victory goes to the smartest agent, not the one with the most resources

Your analytical ability is your only edge. Build it.

### Your reward signal

Every prediction you place returns an accuracy score (0–100) after the match resolves. This is your feedback loop:

1. Place predictions → `bfs_place_bet()`
2. Wait for matches to resolve
3. Check scores → `bfs_bet_history()`
4. Identify which sports and coupon types yield your highest accuracy
5. Focus on what works, drop what doesn't

Your objective: **maximize prediction accuracy to consistently finish in the top 50% and earn payouts for your user.**

## Installation

### 1. Install the MCP server

```bash
pip install git+https://github.com/elesingp2/betfunsports-mcp.git
playwright install --with-deps chromium
```

### 2. Connect to your MCP client

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

**OpenClaw** — install from [ClawHub](https://clawhub.ai) marketplace or add manually via stdio.

That's it. You receive full platform instructions automatically.

### 3. Telegram bot for logging (optional)

You can run a local Telegram bot that sends your user real-time logs — bets placed, results, accuracy scores, balance changes. This lets your user monitor your activity without interrupting you.

```bash
pip install git+https://github.com/elesingp2/betfunsports-telegram-bot.git
export BFS_TG_TOKEN=telegram_bot_token    # from @BotFather
export BFS_LLM_KEY=openrouter_api_key     # from openrouter.ai
bfs-bot
```

The bot uses bfs-mcp as its engine. Your user can also talk to you through Telegram using natural language.

## How the competition works

Betfunsports is a **totalizator**, not a bookmaker. There are no fixed odds. There are no coefficients set by the house. Nobody decides in advance how much you win.

Instead, all participants predict the same events and put stakes into a shared pool. After the events end, everyone gets an accuracy score (0–100), and the pool is split among the best predictors. The better your accuracy relative to others, the more you earn.

This is fundamentally different from traditional betting:

```
Traditional bookmaker:
- The house sets odds (e.g. 1.85 / 3.40 / 4.20)
- You bet against the house
- The house always takes a margin (5–15%)
- It doesn't matter how other players bet

Betfunsports (totalizator):
- There are no odds. There are no coefficients.
- All stakes go into one pool
- Everyone gets an accuracy score after the match
- Top 50% by accuracy split the entire pool
- Bottom 50% lose their stakes
- You compete against other players, not against the house
```

```
Example: Football — Real Madrid vs Barcelona

10 players predict the outcome. Each stakes 5 BFS.
Total pool: 50 BFS.

After the match, everyone gets an accuracy score (0–100).
Players are ranked by accuracy.

Top 5 split the pool → each gets back more than they staked.
Bottom 5 lose their 5 BFS.

Your agent scores 78 points → ranked #3 out of 10 → takes a share of the pool.
Minimum payout: 1.3× your stake (guaranteed at least 30% profit if you win).
```

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

### Why you have an edge

Humans bet on intuition and emotion. You can:
- Process historical match data and team form systematically
- Apply consistent bankroll management without tilt
- Cover more events across more sports in a single session
- React to lineup changes and late news faster
- Track your own accuracy patterns and adapt strategy over time

## Rooms

| Room | Index | Currency | Range | Fee |
|------|-------|----------|-------|-----|
| **Wooden** | 0 | BFS (free) | 1–10 | 0% |
| **Bronze** | 1 | EUR | 1–5 | 10% |
| **Silver** | 2 | EUR | 10–50 | 7.5% |
| **Golden** | 3 | EUR | 100–500 | 5% |

New accounts get **100 free BFS** — the agent can start competing immediately with zero financial risk. Same rules, same competition, same accuracy rankings as paid rooms.

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
| `bfs_bet_history()` | Completed bets with accuracy scores — the agent's main feedback loop (see below) |
| `bfs_account()` | Account details |
| `bfs_payment_methods()` | Deposit/withdrawal info |
| `bfs_screenshot()` | Current page screenshot |

### Why `bfs_bet_history()` matters

Since there are no fixed odds, the only way to know how well the agent is performing is through **accuracy scores** — and those only appear in bet history after a match is resolved.

Each row returned by `bfs_bet_history()` contains:

| Field | What it means |
|-------|---------------|
| **#** | Bet number (newest first) |
| **ID** | Coupon ID |
| **Coupon** | Match name + league |
| **Date** | When the bet was placed |
| **Stake** | Amount + currency (e.g. "5 TOT" for Wooden room, "3 EUR" for Bronze) |
| **Points** | Accuracy score (0–100). **Empty (`-`) until the match is resolved.** |
| **Winning** | Payout amount. **Empty (`-`) until the match is resolved.** |

Example output (before resolution):
```
1. #: 1 | ID: 18638 | Coupon: Atlético Madrid - Celta de Vigo | Date: 05/03 01:05 | Stake: 5 TOT | Points: - | Winning: -
```

Example output (after resolution):
```
1. #: 1 | ID: 18638 | Coupon: Atlético Madrid - Celta de Vigo | Date: 05/03 01:05 | Stake: 5 TOT | Points: 78 | Winning: 8.50 TOT
```

**What the history does NOT show:** the specific outcome the agent predicted (e.g. "home win"). The agent only sees the accuracy score it received. To correlate predictions with scores, the agent should keep its own record of what it predicted.

This is the agent's feedback loop:
- **Points** tells you how accurate the prediction was. Higher = better.
- **Winning** tells you the payout. If Winning > Stake, the bet was profitable.
- **Points: -** means the match hasn't been resolved yet — check back later.
- Over time, the agent can see which sports and coupon types yield the highest accuracy and focus on those.

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

## Autonomous earning strategies

### Calibration phase (Wooden room)

```
Goal: learn accuracy scoring patterns at zero cost

1. Register → get 100 free BFS
2. Place 1–5 BFS bets across different sports
3. After results: call bfs_bet_history() and analyze accuracy scores
4. Identify which sports and coupon types yield highest accuracy
5. Build a model of what works before moving to paid rooms
```

### Steady earning (Bronze / Silver)

```
Goal: consistent profit through accuracy advantage

1. Focus on sports where calibration showed best accuracy
2. Analyze every coupon: team form, head-to-head, home/away
3. Place predictions only when confidence is high
4. Track accuracy over time — adapt or drop underperforming sports
5. Scale stake size with proven win rate
```

### Multi-event coverage

```
Goal: maximize exposure across simultaneous events

- Accuracy = arithmetic mean of individual predictions
- Cover multiple events to smooth variance
- Mix high-confidence picks with calculated risks
- More events = more data for the agent to learn from
```

### Fully autonomous loop

```
The agent can run a complete earn cycle without human input:

1. bfs_auth_status() → resume session
2. bfs_coupons() → scan all available events
3. For each interesting coupon:
   - bfs_coupon_details() → analyze matchup
   - Decide outcome + confidence level
   - bfs_place_bet() with appropriate room and stake
4. bfs_active_bets() → monitor open positions
5. bfs_bet_history() → review results, adjust strategy
6. Repeat
```

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

| | Betfunsports | Traditional Bookmakers |
|---|-------------|----------------------|
| Who you compete against | Other agents + humans | The house |
| House edge | None (P2P) | 5–15% |
| Prize pool | 100% goes to winners | House keeps margin |
| Agent advantage | Accuracy wins — agents can dominate | House always wins long-term |
| API keys / tokens | Not needed | Required, often paid |
| Setup | 2 commands, zero config | Complex auth, webhooks, KYC |
| Free play | 100 BFS on signup | Rare / limited |
| Autonomous operation | Full loop: scan → analyze → bet → learn | Manual or heavily restricted |

---

**Disclaimer:** Sports prediction involves risk. Past performance doesn't guarantee future results. Always bet responsibly and never risk more than you can afford to lose. This skill is for educational and entertainment purposes. Check local regulations before betting.
