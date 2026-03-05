# BFS Agent Skill

P2P sports prediction platform. All stakes go into a shared pool — top 50% by accuracy take everything. No bookmaker, no house edge.

New accounts get **100 free BFS**. Credentials auto-saved after login/registration to `~/.bfs-mcp/`.

## Workflow

```
1. bfs_auth_status()                              → check session first
2. bfs_login(email, password)                     → authenticate (omit args to reuse saved creds)
3. bfs_coupons()                                  → list events
4. bfs_coupon_details(path)                       → outcomes + rooms (ALWAYS call before betting)
5. bfs_place_bet(path, selections, room_index)    → place bet
6. bfs_active_bets()                              → open positions
7. bfs_bet_history()                              → results + accuracy scores (feedback loop)
```

## Tools

| Tool | Args | Description |
|------|------|-------------|
| `bfs_auth_status` | — | Session check + balances. **Call first.** |
| `bfs_login` | email?, password? | Login. Pass creds when user provides them. Omit both → saved creds. |
| `bfs_logout` | — | End session. |
| `bfs_register` | username, email, password, first_name, last_name, birth_date (DD/MM/YYYY), phone, country_code? | Create account. Password: 8+ chars, upper+lower+digits+symbols. Needs email confirmation. |
| `bfs_confirm_registration` | confirmation_url | Activate account via email link. |
| `bfs_coupons` | — | List coupons → `[{path, label}]`. |
| `bfs_coupon_details` | path | Events, outcomes, rooms. **Always call before betting.** |
| `bfs_place_bet` | coupon_path, selections (JSON `{"eventId":"outcomeCode"}`), room_index?, stake? | Place bet. |
| `bfs_active_bets` | — | Unresolved bets. |
| `bfs_bet_history` | — | Full history with accuracy scores. |
| `bfs_account` | — | Account details. |
| `bfs_payment_methods` | — | Deposit/withdrawal info. |
| `bfs_screenshot` | full_page? | Page screenshot (PNG). Default: viewport only. |

## 1X2 Outcome Codes

- `"8"` = **1** (home win)
- `"9"` = **X** (draw)
- `"10"` = **2** (away win)

## Rooms

| Index | Room | Currency | Range | Fee |
|-------|------|----------|-------|-----|
| 0 | Wooden | BFS (free) | 1–10 | 0% |
| 1 | Bronze | EUR | 1–5 | 10% |
| 2 | Silver | EUR | 10–50 | 7.5% |
| 3 | Golden | EUR | 100–500 | 5% |

## Scoring & Payouts

- Accuracy 0–100 per prediction. Multi-event coupons: arithmetic mean.
- Top 50% by accuracy split the pool. Bottom 50% lose stake.
- 100-point predictions always win. Minimum payout: 1.3x stake.
- Tiebreakers: accuracy → stake size → time placed.

## Sports & Coupon Types

- **Football**: 1X2, Correct Score, Goal Difference, Match Winner
- **Tennis**: Match Score (sets), Match Winner, Set Score
- **Hockey**: Match outcome (regulation/OT/shootouts), Goal Difference
- **Basketball**: Match outcome (regulation/OT), Points Difference
- **F1**: Race winner, top 3, team placements
- **Biathlon / Volleyball / Boxing / MMA**: various

## "Player already logged in" Error

One session per account. The server auto-retries with cookie-clear and backoff. If it still fails, tell the user to wait a few minutes or close other sessions.

## Strategy Notes

- Use Wooden room (free BFS) to calibrate before spending EUR.
- `bfs_bet_history()` accuracy scores are your feedback loop — track which sports yield highest accuracy.
- Cover multiple events per coupon to smooth variance.
- Only bet when confidence is high.
