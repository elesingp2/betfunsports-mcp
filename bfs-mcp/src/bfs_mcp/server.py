"""BFS MCP Server — headless browser bridge for betfunsports.com."""

from __future__ import annotations

import json
import logging
from typing import Any

from mcp.server.fastmcp import FastMCP

from .browser import BFSBrowser

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s %(message)s")

mcp = FastMCP(
    "bfs-browser",
    instructions="""\
MCP server that drives betfunsports.com through a headless Chromium browser (Playwright).
No API — all interaction goes through the real website DOM.

## About Betfunsports (TOTUP system)
P2P sports prediction platform. Player bets form a prize pool distributed among winners.
- 50% of bets win (ranked by forecast accuracy 0-100 points)
- Winnings proportional to accuracy × bet size, min coefficient 1.3
- 4 rooms: Wooden (BFS, free, 1-10), Bronze (EUR, 1-5, 10% fee), Silver (EUR, 10-50, 7.5%), Golden (EUR, 100-500, 5%)
- Sports: football, tennis, hockey, basketball, F1, biathlon, volleyball, boxing, MMA
- Coupon types: 1X2 (match outcome), Score, Goal Difference, Match Winner, etc.

## Betting flow
1. Call bfs_state to check auth
2. Call bfs_login if needed
3. Call bfs_list_sports to find coupons
4. Call bfs_bet_info(path) to get events, outcomes, rooms
5. Call bfs_place_bet(coupon_path, selections={eventId: outcomeCode}, room_index, stake)
   - 1X2 outcome codes: "8"=home win(1), "9"=draw(X), "10"=away win(2)

## Key URLs
- Homepage: /
- Sports: /football/prizecoupons1X2, /football/prizecouponsScore, /hockey/kHLRegular, etc.
- Specific coupon: /FOOTBALL/spainPrimeraDivision/18638
- Registration: /fullRegistration
- Profile: /profile
- Payment: /paymentmethods
""",
)

_bm = BFSBrowser()


def _json(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, default=str)


async def _ensure():
    await _bm.start()


# ── auth ──────────────────────────────────────────────────────────────

@mcp.tool()
async def bfs_login(email: str, password: str) -> str:
    """Login to betfunsports.com. Returns auth state and balance."""
    await _ensure()
    return _json((await _bm.login(email, password)).to_dict())


@mcp.tool()
async def bfs_logout() -> str:
    """Logout and clear session."""
    await _ensure()
    return _json(await _bm.logout())


@mcp.tool()
async def bfs_state() -> str:
    """Current state: URL, auth, username, EUR/BFS balance."""
    await _ensure()
    return _json((await _bm.state()).to_dict())


# ── BFS domain ────────────────────────────────────────────────────────

@mcp.tool()
async def bfs_list_sports() -> str:
    """List all sports / coupons from the homepage."""
    await _ensure()
    return _json(await _bm.list_sports())


@mcp.tool()
async def bfs_bet_info(path: str) -> str:
    """Parse coupon page into structured betting info: events, outcomes, rooms.
    Example path: /FOOTBALL/spainPrimeraDivision/18638"""
    await _ensure()
    return _json(await _bm.bet_info(path))


@mcp.tool()
async def bfs_place_bet(coupon_path: str, selections: str,
                        room_index: int = 0, stake: str = "") -> str:
    """Place a bet. selections is JSON: {"eventId": "outcomeCode"}.
    Outcome codes for 1X2: 8=home, 9=draw, 10=away.
    room_index: 0=Wooden(TOT) 1=Bronze(EUR) 2=Silver(EUR) 3=Golden(EUR)."""
    await _ensure()
    sel = json.loads(selections) if isinstance(selections, str) else selections
    return _json(await _bm.place_bet(coupon_path, sel, room_index, stake or None))


# ── browser generic ──────────────────────────────────────────────────

@mcp.tool()
async def browser_navigate(url: str) -> str:
    """Navigate to URL or path (e.g. /football/prizecoupons1X2)."""
    await _ensure()
    return _json(await _bm.goto(url))


@mcp.tool()
async def browser_text(selector: str = "#row-content") -> str:
    """Get visible text from the page. Use 'body' for everything."""
    await _ensure()
    return (await _bm.text(selector))[:5000]


@mcp.tool()
async def browser_html(selector: str = "#row-content") -> str:
    """Get inner HTML of an element."""
    await _ensure()
    return (await _bm.html(selector))[:8000]


@mcp.tool()
async def browser_fill(selector: str, value: str, force: bool = False) -> str:
    """Fill a form field. force=true bypasses visibility checks."""
    await _ensure()
    return await _bm.fill(selector, value, force=force)


@mcp.tool()
async def browser_click(selector: str, force: bool = False) -> str:
    """Click an element. force=true clicks hidden elements."""
    await _ensure()
    return await _bm.click(selector, force=force)


@mcp.tool()
async def browser_select(selector: str, value: str) -> str:
    """Select an option in a dropdown."""
    await _ensure()
    return await _bm.select(selector, value)


@mcp.tool()
async def browser_screenshot(full_page: bool = False) -> str:
    """Take a screenshot. Returns base64 PNG."""
    await _ensure()
    return f"data:image/png;base64,{await _bm.screenshot(full_page)}"


@mcp.tool()
async def browser_eval(javascript: str) -> str:
    """Execute JavaScript in the page and return the result."""
    await _ensure()
    return _json(await _bm.evaluate(javascript))[:5000]


@mcp.tool()
async def browser_forms() -> str:
    """List all forms with their fields."""
    await _ensure()
    return _json(await _bm.forms())[:5000]


@mcp.tool()
async def browser_links(filter_pattern: str = "") -> str:
    """List links on current page with optional filter."""
    await _ensure()
    return _json(await _bm.links(filter_pattern))


@mcp.tool()
async def browser_wait(ms: int = 2000) -> str:
    """Wait N milliseconds."""
    await _ensure()
    await _bm.wait(ms)
    return f"waited {ms}ms"


# ── entry point ───────────────────────────────────────────────────────

def main():
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
