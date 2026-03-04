"""
BFS MCP Server — headless browser bridge for betfunsports.com.

Exposes Playwright-driven tools via the Model Context Protocol,
allowing any MCP-compatible agent to interact with the site
end-to-end without an API.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from typing import Any

from mcp.server.fastmcp import FastMCP

from bfs_mcp.browser import BrowserManager, PageState

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s %(message)s",
)
logger = logging.getLogger("bfs-mcp")

mcp = FastMCP(
    "bfs-browser",
    instructions=(
        "MCP server for betfunsports.com — drives a headless Chromium browser. "
        "No API required: all interaction goes through the real website DOM."
    ),
)

bm = BrowserManager()


def _state_dict(s: PageState) -> dict[str, Any]:
    return {
        "url": s.url,
        "title": s.title,
        "authenticated": s.is_authenticated,
        "username": s.username,
        "balance_eur": s.balance_eur,
        "balance_bfs": s.balance_bfs,
        "in_game": s.in_game,
    }


# ── BFS domain tools ─────────────────────────────────────────────────

@mcp.tool()
async def bfs_login(email: str, password: str) -> str:
    """
    Login to betfunsports.com.
    If the account is already logged in elsewhere, the server may block
    the login with "Player already logged in".
    Returns current page state after login attempt.
    """
    await bm.start()
    state = await bm.login(email, password)
    return json.dumps(_state_dict(state), ensure_ascii=False)


@mcp.tool()
async def bfs_logout() -> str:
    """Logout from betfunsports.com and clear the session."""
    await bm.start()
    result = await bm.logout()
    return json.dumps(result)


@mcp.tool()
async def bfs_state() -> str:
    """
    Get current page state: URL, title, auth status, username,
    EUR balance, BFS balance, in-game amount.
    """
    await bm.start()
    state = await bm.get_state()
    return json.dumps(_state_dict(state), ensure_ascii=False)


@mcp.tool()
async def bfs_list_sports() -> str:
    """
    List all available sports / coupons on the homepage.
    Returns an array of {path, label} objects.
    """
    await bm.start()
    sports = await bm.list_sports()
    return json.dumps(sports, ensure_ascii=False)


@mcp.tool()
async def bfs_view_coupon(path: str) -> str:
    """
    View a specific coupon page (e.g. /football/prizecoupons1X2).
    Returns page title, tables (matches/data), forms (bet inputs),
    and a text summary of the page content.
    """
    await bm.start()
    details = await bm.get_coupon_details(path)
    return json.dumps(details, ensure_ascii=False)


@mcp.tool()
async def bfs_get_profile() -> str:
    """
    Navigate to the user profile page and extract its content.
    Requires prior login.
    """
    await bm.start()
    nav = await bm.goto("/profile")
    text = await bm.get_text("#row-content")
    return json.dumps({**nav, "text": text[:3000]}, ensure_ascii=False)


@mcp.tool()
async def bfs_get_balance() -> str:
    """
    Quick balance check. Navigates to homepage and extracts
    EUR balance, BFS balance, and in-game amount.
    """
    await bm.start()
    await bm.goto("/")
    state = await bm.get_state()
    return json.dumps({
        "username": state.username,
        "balance_eur": state.balance_eur,
        "balance_bfs": state.balance_bfs,
        "in_game": state.in_game,
        "authenticated": state.is_authenticated,
    }, ensure_ascii=False)


@mcp.tool()
async def bfs_payment_info() -> str:
    """View the payment / deposit page content."""
    await bm.start()
    nav = await bm.goto("/paymentmethods")
    text = await bm.get_text("#row-content")
    return json.dumps({**nav, "text": text[:3000]}, ensure_ascii=False)


# ── Generic browser tools ────────────────────────────────────────────

@mcp.tool()
async def browser_navigate(url: str) -> str:
    """
    Navigate to a URL (absolute or relative path like /football/prizecoupons1X2).
    Returns status code, final URL, and page title.
    """
    await bm.start()
    result = await bm.goto(url)
    return json.dumps(result, ensure_ascii=False)


@mcp.tool()
async def browser_get_text(selector: str = "body") -> str:
    """
    Extract visible text from the current page.
    Default selector is 'body'. Use '#row-content' for main content only.
    """
    await bm.start()
    text = await bm.get_text(selector)
    return text[:5000]


@mcp.tool()
async def browser_get_html(selector: str = "#row-content") -> str:
    """
    Get inner HTML of an element on the current page.
    Useful for inspecting DOM structure, forms, tables.
    """
    await bm.start()
    html = await bm.get_html(selector)
    return html[:10000]


@mcp.tool()
async def browser_fill(selector: str, value: str, force: bool = False) -> str:
    """
    Fill a form field by CSS selector.
    Set force=true to bypass visibility checks (for hidden/honeypot fields).
    """
    await bm.start()
    return await bm.fill(selector, value, force=force)


@mcp.tool()
async def browser_click(selector: str, force: bool = False) -> str:
    """
    Click an element by CSS selector.
    Set force=true to click hidden/covered elements.
    """
    await bm.start()
    return await bm.click(selector, force=force)


@mcp.tool()
async def browser_select(selector: str, value: str) -> str:
    """Select an option in a <select> dropdown by value."""
    await bm.start()
    return await bm.select(selector, value)


@mcp.tool()
async def browser_screenshot(full_page: bool = False) -> str:
    """
    Take a screenshot of the current page.
    Returns base64-encoded PNG. Set full_page=true for full scroll capture.
    """
    await bm.start()
    b64 = await bm.screenshot(full_page=full_page)
    return f"data:image/png;base64,{b64}"


@mcp.tool()
async def browser_eval(javascript: str) -> str:
    """
    Execute arbitrary JavaScript in the page context.
    Returns the JSON-serialized result.
    Use for complex DOM queries, form manipulation, data extraction.
    """
    await bm.start()
    result = await bm.evaluate(javascript)
    return json.dumps(result, ensure_ascii=False, default=str)


@mcp.tool()
async def browser_wait(ms: int = 2000) -> str:
    """Wait for a specified number of milliseconds. Useful after clicks/navigation."""
    await bm.start()
    return await bm.wait(ms)


@mcp.tool()
async def browser_forms() -> str:
    """
    List all forms on the current page with their fields.
    Useful for understanding what data a page expects.
    """
    await bm.start()
    forms = await bm.evaluate("""() => {
        return Array.from(document.forms).map(f => ({
            id: f.id || '(unnamed)',
            action: f.action,
            method: f.method,
            fields: Array.from(f.elements).filter(e => e.name).map(e => ({
                name: e.name,
                type: e.type,
                value: (e.value || '').substring(0, 80),
                visible: e.offsetParent !== null,
                options: e.tagName === 'SELECT'
                    ? Array.from(e.options).slice(0, 10).map(o => o.value)
                    : undefined,
            }))
        })).filter(f => f.fields.length > 0);
    }""")
    return json.dumps(forms, ensure_ascii=False)


@mcp.tool()
async def browser_links(filter_pattern: str = "") -> str:
    """
    List all links on the current page.
    Optional filter_pattern (substring match on href).
    """
    await bm.start()
    links = await bm.evaluate(f"""() => {{
        const pattern = "{filter_pattern}";
        return Array.from(document.querySelectorAll('a[href]'))
            .map(a => ({{href: a.getAttribute('href'), text: a.textContent.trim().replace(/\\s+/g, ' ').substring(0, 100)}}))
            .filter(l => l.href && (!pattern || l.href.includes(pattern)))
            .filter((v, i, a) => a.findIndex(x => x.href === v.href) === i)
            .slice(0, 100);
    }}""")
    return json.dumps(links, ensure_ascii=False)


# ── Server entry point ────────────────────────────────────────────────

def main():
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
