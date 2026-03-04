"""BFS MCP Server — headless browser bridge for betfunsports.com."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from mcp.server.fastmcp import FastMCP

from .browser import BFSBrowser

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s %(message)s")

_SKILL = (Path(__file__).resolve().parent.parent.parent / "skill.md").read_text(encoding="utf-8")

mcp = FastMCP("bfs", instructions=_SKILL)

_b = BFSBrowser()
_j = lambda x: json.dumps(x, ensure_ascii=False, default=str)

async def _e():
    await _b.start()


# ── Registration & auth ──────────────────────────────────────────────

@mcp.tool()
async def bfs_register(username: str, email: str, password: str,
                       first_name: str, last_name: str, birth_date: str,
                       phone: str, country_code: str = "US",
                       city: str = "", address: str = "", zip_code: str = "") -> str:
    """Register a new account on betfunsports.com.
    birth_date format: DD/MM/YYYY. country_code: ISO 2-letter (US, DE, GB, etc.).
    Password: min 8 chars, mix of upper/lower/numbers/symbols.
    City, address and zip_code are required by the form — if empty, placeholders are used.
    After registration, user must confirm email via link sent to their inbox.
    New accounts get 100 free BFS for Wooden room betting."""
    await _e()
    return _j(await _b.register(username, email, password, first_name, last_name,
                                birth_date, phone, country_code, city, address, zip_code))


@mcp.tool()
async def bfs_confirm_registration(confirmation_url: str) -> str:
    """Activate a registered account by visiting the confirmation link from email.
    Pass the full URL from the confirmation email (e.g. https://betfunsports.com/confirm/...)."""
    await _e()
    return _j(await _b.confirm_registration(confirmation_url))


@mcp.tool()
async def bfs_login(email: str, password: str) -> str:
    """Authenticate. Returns balances or error.
    If 'Player already logged in' — the user must logout from their other session first."""
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


# ── Betting ──────────────────────────────────────────────────────────

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


# ── Monitoring ───────────────────────────────────────────────────────

@mcp.tool()
async def bfs_active_bets() -> str:
    """Get currently active (unresolved) bets waiting for event results.
    Returns CSV with: ID, Coupon, Date, Stake."""
    await _e()
    return _j(await _b.active_bets())


@mcp.tool()
async def bfs_bet_history() -> str:
    """Export bet history as CSV: ID, Coupon, Date, Stake, Points (accuracy), Winning.
    Use for strategy analysis."""
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


# ── Page tools (advanced) ────────────────────────────────────────────

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
