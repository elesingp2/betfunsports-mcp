# BFS Browser Skill

You have access to the `bfs-browser` MCP server that controls betfunsports.com through a headless browser. Use the available tools to interact with the site.

## About Betfunsports

Betfunsports is a P2P sports prediction platform. Players compete for a prize pool formed by their bets. 50% of bets win, ranked by forecast accuracy (0-100 points). Winnings are proportional to accuracy × bet size.

### Rooms (tables)
| Room | Index | Currency | Range | Fee |
|------|-------|----------|-------|-----|
| Wooden | 0 | BFS (free) | 1-10 | 0% |
| Bronze | 1 | EUR | 1-5 | 10% |
| Silver | 2 | EUR | 10-50 | 7.5% |
| Golden | 3 | EUR | 100-500 | 5% |

### Sports & coupon types
Football, tennis, hockey, basketball, F1, biathlon, volleyball, boxing, MMA.
Coupon types: 1X2 (match outcome), Score, Goal Difference, Match Winner, Playoff, etc.

### 1X2 outcome codes
- `"8"` = 1 (home win)
- `"9"` = X (draw)
- `"10"` = 2 (away win)

## How to place a bet

```
1. bfs_state              → check if logged in
2. bfs_login(email, pw)   → login if needed
3. bfs_list_sports        → browse available coupons
4. bfs_bet_info(path)     → get events, outcomes, rooms for a coupon
5. bfs_place_bet(         → place the bet
     coupon_path="/FOOTBALL/...",
     selections={"19852": "8"},   ← eventId: outcomeCode
     room_index=0,                ← 0=Wooden (free)
     stake="1"
   )
6. browser_screenshot     → verify result
```

## Available tools

### BFS domain
- `bfs_login(email, password)` — login (handles anti-bot protection)
- `bfs_logout()` — logout
- `bfs_state()` — auth status, username, EUR/BFS balances
- `bfs_list_sports()` — all available coupons
- `bfs_bet_info(path)` — parse coupon into events/outcomes/rooms
- `bfs_place_bet(coupon_path, selections, room_index, stake)` — place a bet

### Browser generic
- `browser_navigate(url)` — go to any page
- `browser_text(selector)` — extract text
- `browser_html(selector)` — get HTML
- `browser_click(selector)` — click element
- `browser_fill(selector, value)` — fill input
- `browser_select(selector, value)` — select dropdown
- `browser_screenshot()` — take screenshot
- `browser_eval(javascript)` — run JS
- `browser_forms()` — list all forms
- `browser_links(filter)` — list links
- `browser_wait(ms)` — wait

## Tips
- Always call `bfs_bet_info` before `bfs_place_bet` to get correct eventId and roomId
- Recommend Wooden room (free BFS) for new users
- If a coupon says "Bets are not possible" — it's closed, find another
- The site uses honeypot fields in forms — `bfs_login` handles this automatically
- After placing a bet, check balance with `bfs_state`
