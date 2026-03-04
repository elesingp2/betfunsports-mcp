"""BFS MCP Server — platform API for betfunsports.com."""

from __future__ import annotations

import json
import logging
from typing import Any

from mcp.server.fastmcp import FastMCP

from .browser import BFSBrowser

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s %(message)s")

mcp = FastMCP(
    "bfs",
    instructions="""\
# Betfunsports Platform API

API for betfunsports.com — a P2P sports prediction platform where players compete for prize pools.

## How it works
- Players place bets (forecasts) on sports events via coupons
- All bets form a prize pool that is FULLY distributed among winners
- Top 50% of bets win, ranked by forecast accuracy (0-100 points)
- Winnings are proportional to accuracy × bet size (min coefficient 1.3)

## Rooms (tables)
| Room    | Index | Currency      | Range   | Fee  |
|---------|-------|---------------|---------|------|
| Wooden  | 0     | BFS (free)    | 1-10    | 0%   |
| Bronze  | 1     | EUR           | 1-5     | 10%  |
| Silver  | 2     | EUR           | 10-50   | 7.5% |
| Golden  | 3     | EUR           | 100-500 | 5%   |

Start with Wooden (free BFS) to learn, then move to Bronze/Silver/Golden to earn EUR.

## Sports & coupon types
Football, tennis, hockey, basketball, Formula 1, biathlon, volleyball, boxing, MMA.
Main coupon types: 1X2 (match outcome), Score (exact score), Goal Difference, Match Winner.

## Earning strategy
1. Authenticate → browse available coupons → analyze events
2. Export bet history (CSV) to study past accuracy patterns
3. Place bets where you have highest confidence in outcome
4. Wooden room for testing strategy (free), Silver/Golden for real earnings
5. Accuracy is key: 100-point forecasts ALWAYS win, even if >50% get them

## Betting flow
1. `bfs_auth_status` — check if logged in
2. `bfs_login` — authenticate
3. `bfs_coupons` — browse available coupons
4. `bfs_coupon_details` — get events, outcomes, rooms for a specific coupon
5. `bfs_place_bet` — place the bet
6. `bfs_bet_history` — review past bets and results (CSV export)

## 1X2 outcome codes
- "8" = 1 (home win), "9" = X (draw), "10" = 2 (away win)
""",
)

_b = BFSBrowser()
_j = lambda x: json.dumps(x, ensure_ascii=False, default=str)

async def _e():
    await _b.start()


# ── Platform API ──────────────────────────────────────────────────────

@mcp.tool()
async def bfs_register(username: str, email: str, password: str,
                       first_name: str, last_name: str, birth_date: str,
                       phone: str, country_code: str = "US",
                       city: str = "", address: str = "", zip_code: str = "") -> str:
    """Register a new account on betfunsports.com.
    birth_date format: DD/MM/YYYY. country_code: ISO 2-letter (US, DE, GB, etc.).
    Password: min 8 chars, mix of upper/lower/numbers/symbols.
    New accounts get 100 free BFS for Wooden room betting."""
    await _e()
    return _j(await _b.register(username, email, password, first_name, last_name,
                                birth_date, phone, country_code, city, address, zip_code))


@mcp.tool()
async def bfs_login(email: str, password: str) -> str:
    """Authenticate. Returns balances or error if account is already logged in elsewhere.
    If error='invalidLoginMessage=Player+already+logged+in', the user must logout from their other session first."""
    await _e()
    return _j(await _b.login(email, password))


@mcp.tool()
async def bfs_logout() -> str:
    """End session."""
    await _e()
    return _j(await _b.logout())


@mcp.tool()
async def bfs_auth_status() -> str:
    """Check authentication and get current balances (EUR, BFS, in-game amount)."""
    await _e()
    return _j((await _b.state()).to_dict())


@mcp.tool()
async def bfs_active_bets() -> str:
    """Get currently active (unresolved) bets. These are bets waiting for event results.
    Returns CSV with: ID, Coupon, Date, Stake. Use for portfolio monitoring."""
    await _e()
    return _j(await _b.active_bets())


@mcp.tool()
async def bfs_coupons() -> str:
    """List all available sports coupons for betting.
    Returns array of {path, label} — use path in bfs_coupon_details."""
    await _e()
    return _j(await _b.list_sports())


@mcp.tool()
async def bfs_coupon_details(path: str) -> str:
    """Get full details of a coupon: events (matches), available outcomes,
    betting rooms with min/max stakes. ALWAYS call before placing a bet.
    Example: bfs_coupon_details("/FOOTBALL/spainPrimeraDivision/18638")"""
    await _e()
    return _j(await _b.bet_info(path))


@mcp.tool()
async def bfs_place_bet(coupon_path: str, selections: str,
                        room_index: int = 0, stake: str = "") -> str:
    """Place a bet on a coupon.
    - coupon_path: from bfs_coupon_details
    - selections: JSON {"eventId": "outcomeCode"} — for 1X2: "8"=home, "9"=draw, "10"=away
    - room_index: 0=Wooden(BFS,free) 1=Bronze(1-5€) 2=Silver(10-50€) 3=Golden(100-500€)
    - stake: amount (string). Empty = room default."""
    await _e()
    sel = json.loads(selections) if isinstance(selections, str) else selections
    return _j(await _b.place_bet(coupon_path, sel, room_index, stake or None))


@mcp.tool()
async def bfs_bet_history() -> str:
    """Export bet history as CSV. Contains: ID, Coupon, Date, Stake, Points (accuracy), Winning.
    Use this data to analyze prediction patterns and improve accuracy."""
    await _e()
    return _j(await _b.bet_history())


@mcp.tool()
async def bfs_account() -> str:
    """Get account details: name, email, registration info."""
    await _e()
    return _j(await _b.account_info())


@mcp.tool()
async def bfs_payment_methods() -> str:
    """View available deposit and withdrawal methods with fees and limits."""
    await _e()
    await _b.goto("/paymentmethods")
    return (await _b.text("#row-content"))[:4000]


# ── Low-level page tools ─────────────────────────────────────────────

@mcp.tool()
async def page_open(url: str) -> str:
    """Open a page by URL or path. Returns status, final URL, title."""
    await _e()
    return _j(await _b.goto(url))


@mcp.tool()
async def page_read(selector: str = "#row-content") -> str:
    """Read text content from current page. Use '#row-content' for main area, 'body' for all."""
    await _e()
    return (await _b.text(selector))[:5000]


@mcp.tool()
async def page_click(selector: str) -> str:
    """Click an element on the page."""
    await _e()
    return await _b.click(selector, force=True)


@mcp.tool()
async def page_fill(selector: str, value: str) -> str:
    """Fill a form field."""
    await _e()
    return await _b.fill(selector, value, force=True)


@mcp.tool()
async def page_select(selector: str, value: str) -> str:
    """Select an option in a dropdown."""
    await _e()
    return await _b.select(selector, value)


@mcp.tool()
async def page_screenshot(full_page: bool = False) -> str:
    """Take a visual snapshot of the current page. Returns base64 PNG."""
    await _e()
    return f"data:image/png;base64,{await _b.screenshot(full_page)}"


@mcp.tool()
async def page_run_script(javascript: str) -> str:
    """Execute a script on the page for advanced data extraction."""
    await _e()
    return _j(await _b.evaluate(javascript))[:5000]


@mcp.tool()
async def page_forms() -> str:
    """List all interactive forms on the current page."""
    await _e()
    return _j(await _b.forms())[:5000]


@mcp.tool()
async def page_links(filter_pattern: str = "") -> str:
    """List links on the current page. Optional substring filter."""
    await _e()
    return _j(await _b.links(filter_pattern))


def main():
    mcp.run(transport="stdio")

if __name__ == "__main__":
    main()
