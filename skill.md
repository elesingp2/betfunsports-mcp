# Betfunsports — Autonomous Earning Skill

You have access to the Betfunsports platform API (`bfs` MCP server). Use it to place sports predictions and earn money.

## What is Betfunsports

A P2P sports prediction platform. Players' bets form a prize pool that is **fully distributed** among winners. There is no house edge — you compete only against other players.

**Key economics:**
- **Top 50% of predictions win** (ranked by accuracy, 0–100 points)
- Winnings = accuracy × bet size (minimum coefficient **1.3**)
- Predictions scoring **100 points always win**, even if more than 50% get them
- The pool is **100% distributed** — the platform only takes a commission fee on entry

## Rooms (tables)

| Room | Index | Currency | Bet range | Commission | Use case |
|------|-------|----------|-----------|------------|----------|
| **Wooden** | 0 | BFS (virtual) | 1–10 | 0% | Testing / learning |
| **Bronze** | 1 | EUR | 1–5 | 10% | Low-risk earning |
| **Silver** | 2 | EUR | 10–50 | 7.5% | Mid-tier earning |
| **Golden** | 3 | EUR | 100–500 | 5% | High-stakes |

## How to earn

### Strategy
1. **Start on Wooden** (free) — learn the scoring system, test prediction accuracy
2. **Export bet history** with `bfs_bet_history` — analyze which sports/coupon types give you highest accuracy
3. **Move to Silver/Golden** once your average accuracy is consistently above the pool median
4. Focus on events where you have an **information edge** — accuracy is everything
5. **Accuracy ranking**: 100-point forecasts always win, 0-point always lose. The tiebreaker is bet size, then time

### Coupon types
- **1X2** — predict match outcome (home/draw/away). Simplest, good for football
- **Score** — predict exact score. Harder but higher accuracy differential
- **Goal Difference** — predict score margin. Good middle ground
- Other: Match Winner, Playoff outcomes, Set scores (tennis), etc.

### 1X2 outcome codes
- `"8"` → **1** (home win)
- `"9"` → **X** (draw)
- `"10"` → **2** (away win)

## Complete betting workflow

```
1. bfs_auth_status()                          → check if logged in
2. bfs_login(email, password)                 → authenticate
3. bfs_coupons()                              → list available coupons
4. bfs_coupon_details("/FOOTBALL/.../18638")   → get events + rooms
5. bfs_place_bet(                             → place bet
     coupon_path="/FOOTBALL/.../18638",
     selections={"19852": "8"},                ← eventId: outcomeCode
     room_index=2,                             ← Silver
     stake="10"                                ← 10 EUR
   )
6. bfs_auth_status()                          → verify balance change
```

## Analytics workflow

```
1. bfs_bet_history()     → CSV with all past bets (ID, Coupon, Date, Stake, Points, Winning)
2. Analyze accuracy distribution — are you consistently in top 50%?
3. Identify best-performing sports/coupon types
4. Adjust strategy: focus on highest-accuracy segments
```

## Available tools

### Platform API (primary)
| Tool | Description |
|------|-------------|
| `bfs_login(email, password)` | Authenticate, get balances |
| `bfs_logout()` | End session |
| `bfs_auth_status()` | Check auth + EUR/BFS balances |
| `bfs_coupons()` | List available coupons [{path, label}] |
| `bfs_coupon_details(path)` | Events, outcomes, rooms for a coupon |
| `bfs_place_bet(...)` | Place a bet (see workflow above) |
| `bfs_bet_history()` | Export bet history as CSV |
| `bfs_account()` | Account details |
| `bfs_payment_methods()` | Deposit/withdrawal methods + fees |

### Page tools (advanced)
| Tool | Description |
|------|-------------|
| `page_open(url)` | Open a page |
| `page_read(selector)` | Read page content |
| `page_click(selector)` | Click element |
| `page_fill(selector, value)` | Fill form field |
| `page_select(selector, value)` | Select dropdown |
| `page_screenshot()` | Visual snapshot |
| `page_script(javascript)` | Run script for data extraction |
| `page_forms()` | List forms on page |
| `page_links(filter)` | List links |

## Important notes
- Always call `bfs_coupon_details` before `bfs_place_bet` — you need the exact eventId
- If a coupon returns `"error": "betting closed"` — find another active coupon
- After placing a bet, check `bfs_auth_status` to confirm balance change
- BFS (Wooden room) is free virtual currency — perfect for testing strategies at zero risk
- Commission is deducted from your account separately, not from the prize pool
