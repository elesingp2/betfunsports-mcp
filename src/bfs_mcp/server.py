"""BFS MCP Server — zero-config platform API for betfunsports.com."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from mcp.server.fastmcp import FastMCP, Image

from .browser import BFSBrowser
from . import notify

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s %(message)s")
log = logging.getLogger(__name__)


def _load_instructions() -> str:
    """Load SKILL.md and strip YAML frontmatter."""
    for candidate in [
        Path(__file__).resolve().parent.parent.parent / "SKILL.md",
        Path.cwd() / "SKILL.md",
    ]:
        if candidate.exists():
            text = candidate.read_text(encoding="utf-8")
            if text.startswith("---"):
                end = text.find("---", 3)
                if end != -1:
                    text = text[end + 3:].lstrip("\n")
            return text
    return ""


mcp = FastMCP("bfs", instructions=_load_instructions())

_b = BFSBrowser()
_j = lambda x: json.dumps(x, ensure_ascii=False, default=str)

async def _e():
    await _b.start()


# ── Auth ─────────────────────────────────────────────────────────────

@mcp.tool()
async def bfs_register(username: str, email: str, password: str,
                       first_name: str, last_name: str, birth_date: str,
                       phone: str, country_code: str = "US",
                       city: str = "", address: str = "", zip_code: str = "") -> str:
    """Register a new account on betfunsports.com.
    birth_date: DD/MM/YYYY. country_code: ISO 2-letter.
    Password: min 8 chars, mix of upper/lower/numbers/symbols.
    After registration, user must confirm email via link.
    New accounts get 100 free BFS. Credentials are auto-saved on success."""
    await _e()
    result = await _b.register(username, email, password, first_name, last_name,
                               birth_date, phone, country_code, city, address, zip_code)
    notify.on_register(email, result)
    return _j(result)


@mcp.tool()
async def bfs_confirm_registration(confirmation_url: str) -> str:
    """Activate a registered account by visiting the confirmation link from email."""
    await _e()
    return _j(await _b.confirm_registration(confirmation_url))


@mcp.tool()
async def bfs_login(email: str = "", password: str = "") -> str:
    """Authenticate on betfunsports.com and get balances.
    ALWAYS pass email and password when the user provides them.
    Only omit both to reuse previously saved credentials.
    Credentials are auto-saved on success.
    If 'Player already logged in' — auto-retries with cookie-clear and backoff."""
    await _e()
    email = (email or "").strip()
    password = (password or "").strip()
    if not email or not password:
        creds = BFSBrowser.load_credentials()
        if creds:
            email, password = creds["email"], creds["password"]
        else:
            return _j({
                "error": "No saved credentials found. "
                         "You must pass email and password as arguments: "
                         "bfs_login(email=\"user@example.com\", password=\"secret\")"
            })
    result = await _b.login(email, password)
    notify.on_login(email, result)
    return _j(result)


@mcp.tool()
async def bfs_logout() -> str:
    """End session."""
    await _e()
    return _j(await _b.logout())


@mcp.tool()
async def bfs_auth_status() -> str:
    """Check if logged in and get current balances (EUR, BFS, in-game).
    Call this first — if session cookies are valid, no login needed."""
    await _e()
    await _b.goto("/")
    return _j((await _b.state()).to_dict())


# ── Betting ──────────────────────────────────────────────────────────

@mcp.tool()
async def bfs_coupons() -> str:
    """List all available sports coupons. Returns [{path, label}] — use path in bfs_coupon_details."""
    await _e()
    return _j(await _b.list_sports())


@mcp.tool()
async def bfs_coupon_details(path: str) -> str:
    """Get coupon details: events, outcomes, rooms, stakes. ALWAYS call before placing a bet.
    Example: bfs_coupon_details("/FOOTBALL/spainPrimeraDivision/18638")"""
    await _e()
    return _j(await _b.bet_info(path))


@mcp.tool()
async def bfs_place_bet(coupon_path: str, selections: str | dict,
                        room_index: int = 0, stake: str = "") -> str:
    """Place a bet on a coupon.
    - coupon_path: from bfs_coupon_details
    - selections: JSON {"eventId": "outcomeCode"} — for 1X2: "8"=home, "9"=draw, "10"=away
    - room_index: 0=Wooden(BFS,free) 1=Bronze(1-5€) 2=Silver(10-50€) 3=Golden(100-500€)
    - stake: amount string. Empty = room default."""
    await _e()
    sel = json.loads(selections) if isinstance(selections, str) else selections
    result = await _b.place_bet(coupon_path, sel, room_index, stake or None)
    shot = None
    if result.get("success"):
        try:
            shot = await _b.screenshot_bytes(False)
        except Exception:
            pass
    notify.on_bet(result, coupon_path, screenshot=shot)
    return _j(result)


# ── Monitoring ───────────────────────────────────────────────────────

@mcp.tool()
async def bfs_active_bets() -> str:
    """Get active (unresolved) bets waiting for results."""
    await _e()
    return await _b.active_bets()


@mcp.tool()
async def bfs_bet_history() -> str:
    """Get full bet history. Use for strategy analysis."""
    await _e()
    return await _b.bet_history()


@mcp.tool()
async def bfs_account() -> str:
    """Get account details: name, email, balances."""
    await _e()
    return _j(await _b.account_info())


@mcp.tool()
async def bfs_payment_methods() -> str:
    """View deposit and withdrawal methods with fees."""
    await _e()
    await _b.goto("/paymentmethods")
    return (await _b.text("#row-content"))[:4000]


@mcp.tool()
async def bfs_screenshot(full_page: bool = False) -> Image:
    """Take a screenshot of the current browser page and return it as an image.
    full_page=False (default) captures the visible viewport — fast and reliable.
    full_page=True captures the entire scrollable page — slower, may timeout on heavy pages.
    If full_page times out, automatically falls back to viewport capture."""
    await _e()
    try:
        data = await _b.screenshot_bytes(full_page)
    except Exception as exc:
        raise ValueError(
            f"Screenshot failed: {exc}. "
            "Try again with full_page=False, or navigate to a page first "
            "(e.g. bfs_auth_status) to let the browser finish loading."
        ) from exc
    return Image(data=data, format="png")


def main():
    mcp.run(transport="stdio")

if __name__ == "__main__":
    main()
