# Betfunsports — Agent Skill

You have access to the Betfunsports platform via the `bfs` MCP server.
Use the tools below to register accounts, authenticate, browse sports events, place bets, and analyze results.

## What is Betfunsports

A P2P sports prediction platform. Players' bets form a prize pool that is **fully distributed** among winners — there is no house edge.

- **Top 50% of predictions win**, ranked by accuracy (0–100 points)
- Winnings are proportional to accuracy × bet size (minimum coefficient **1.3**)
- Predictions scoring **100 points always win**, even if more than 50% achieve them
- The pool is **100% distributed** — the platform takes a commission fee on entry only
- Bets and commission are refunded if: only one bet was placed, all bets scored 100, or the event was cancelled

### Ranking rules

Bets are ranked by three criteria in order:
1. **Accuracy** (descending) — higher score = higher rank
2. **Bet size** (descending) — larger bet wins ties
3. **Time** (ascending) — earlier bet wins ties

## Rooms

| Room | Index | Currency | Range | Fee | Use case |
|------|-------|----------|-------|-----|----------|
| **Wooden** | 0 | BFS (virtual) | 1–10 | 0% | Free practice |
| **Bronze** | 1 | EUR | 1–5 | 10% | Low stakes |
| **Silver** | 2 | EUR | 10–50 | 7.5% | Mid-tier |
| **Golden** | 3 | EUR | 100–500 | 5% | High stakes |

New accounts receive **100 free BFS** for Wooden room betting.

## Sports and coupon types

**Sports:** Football, Tennis, Hockey, Basketball, Formula 1, Biathlon, Volleyball, Boxing, MMA.

### Football
| Coupon type | What to predict |
|-------------|----------------|
| **1X2 (Match outcome)** | 1 = home, X = draw, 2 = away (main time only for playoffs) |
| **Match Winner** | Playoff only — winner including extra time / penalties |
| **Goal Difference** | Margin: ≥3 / 2 / 1 home, draw, 1 / 2 / ≥3 away |
| **Correct Score** | Exact score after main + stoppage time |
| **Score + Half** | Correct match score + correct first half score |

### Tennis
| Coupon type | What to predict |
|-------------|----------------|
| **Match Score** | Set score (e.g. 2-0, 2-1 for best-of-3) |
| **Match Winner** | Who wins the match |
| **Set Score** | Score within a set |
| **Game Score / Winner** | Score or winner of a game |

### Hockey
| Coupon type | What to predict |
|-------------|----------------|
| **Match outcome** | Home/away win in regular time, overtime, or shootouts (6 options) |
| **Outcome+** | Outcome + goal margin range (8 options) |
| **Goal Difference** | Score difference in regular time (up to ±5 goals) |

### Basketball
| Coupon type | What to predict |
|-------------|----------------|
| **Match outcome** | Home/away win in regular time or overtime (4 options) |
| **Points Difference** | Win margin range: 1-6 / 7-12 / >12 for each side |
| **Exact Difference** | Exact point margin |

### Formula 1
Top three finishers, race winner, or team placements (top 10).

### Biathlon
Race winner, winning team, podium finishers.

### Volleyball
Match score by sets, or game score within a set.

## 1X2 outcome codes

For 1X2 coupons, use these codes when calling `bfs_place_bet`:
- `"8"` → **1** (home win)
- `"9"` → **X** (draw)
- `"10"` → **2** (away win)

## Accuracy scoring

- 100 points = perfect prediction (exact match)
- 0 points = worst possible prediction
- Points scale linearly or exponentially based on how close you were
- For multi-event coupons: final score = arithmetic mean of individual scores
- Each coupon type has its own scoring table — check via "Coupon Rules" on the site

## Credential storage

The MCP server does NOT store login credentials between sessions. To avoid re-entering them:

**Cursor / Claude Desktop:** Store credentials in your MCP config or project rules so the agent always has access:
```
BFS account: email=user@example.com password=MyPass@2026!
```

**Telegram bot:** The bot remembers credentials within the conversation history. Just say "log in as user@example.com password" once per session.

**Programmatic:** Set environment variables `BFS_EMAIL` and `BFS_PASSWORD` and have the agent read them.

The agent should call `bfs_auth_status` first — if already authenticated (session cookies persist), no login is needed.

## Tools reference

### Registration and auth

| Tool | Parameters | Description |
|------|-----------|-------------|
| `bfs_register` | `username`, `email`, `password`, `first_name`, `last_name`, `birth_date` (DD/MM/YYYY), `phone`, `country_code` (ISO-2, default "US"), `city`, `address`, `zip_code` | Register new account. Password: min 8 chars, mixed case+numbers+symbols. After registration, user must confirm email via link. Gets 100 free BFS. |
| `bfs_confirm_registration` | `confirmation_url` | Activate account by visiting the confirmation link from email |
| `bfs_login` | `email`, `password` | Authenticate. Returns balances. Auto-retries if "Player already logged in". |
| `bfs_logout` | — | End session |
| `bfs_auth_status` | — | Check auth + balances (EUR, BFS, in-game). **Call this first.** |

### Betting

| Tool | Parameters | Description |
|------|-----------|-------------|
| `bfs_coupons` | — | List available coupons → `[{path, label}]` |
| `bfs_coupon_details` | `path` (e.g. `/FOOTBALL/spainPrimeraDivision/18638`) | Get events, outcomes, rooms, stakes. **Always call before placing a bet.** |
| `bfs_place_bet` | `coupon_path`, `selections` (JSON `{"eventId": "outcomeCode"}`), `room_index` (0-3), `stake` | Place a bet. |

### Monitoring

| Tool | Parameters | Description |
|------|-----------|-------------|
| `bfs_active_bets` | — | Active (unresolved) bets awaiting results (formatted text) |
| `bfs_bet_history` | — | Full bet history (formatted text): ID, Coupon, Date, Stake, Points, Winning |
| `bfs_account` | — | Account details |
| `bfs_payment_methods` | — | Deposit/withdrawal methods and fees |

## Workflows

### New user registration
```
1. bfs_register(username, email, password, first_name, last_name,
                birth_date="DD/MM/YYYY", phone, country_code="US")
   → returns needs_email_confirmation: true
2. User clicks confirmation link in their email
3. bfs_confirm_registration(confirmation_url)   — if you have the link
4. bfs_login(email, password)
```

### Betting flow
```
1. bfs_auth_status()                            → check if logged in
2. bfs_login(email, password)                   → authenticate if needed
3. bfs_coupons()                                → browse available coupons
4. bfs_coupon_details("/FOOTBALL/.../18638")    → get events + outcomes + rooms
5. bfs_place_bet(                               → place the bet
     coupon_path="/FOOTBALL/.../18638",
     selections='{"19852": "8"}',                ← eventId: outcomeCode
     room_index=0,                               ← Wooden (free)
     stake="5"
   )
6. bfs_auth_status()                            → verify balance changed
```

### Strategy optimization
```
1. bfs_bet_history()                            → get full history
2. Analyze: average accuracy by sport / coupon type
3. Focus on segments where accuracy is consistently in top 50%
4. Progress: Wooden → Bronze → Silver → Golden as confidence grows
```

## Key rules

- **Always** call `bfs_coupon_details` before `bfs_place_bet` — you need the exact eventId and outcomeCode
- If a coupon returns `"error": "betting closed"` — the event has already started, pick another coupon
- If login returns "Player already logged in" — the system auto-retries after logout
- Commission is charged separately from the bet, not deducted from the prize pool
- BFS (Wooden room) is free virtual currency — zero-risk strategy testing
