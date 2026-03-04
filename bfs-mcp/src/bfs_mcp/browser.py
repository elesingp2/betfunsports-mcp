"""
Playwright browser manager — persistent headless session for BFS.
Handles lifecycle, auth state, cookie persistence.
"""

from __future__ import annotations

import asyncio
import base64
import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from playwright.async_api import (
    Browser,
    BrowserContext,
    Page,
    Playwright,
    async_playwright,
)

logger = logging.getLogger("bfs-mcp.browser")

BASE_URL = "https://betfunsports.com"
COOKIE_FILE = Path.home() / ".bfs-mcp" / "cookies.json"
UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)


@dataclass
class PageState:
    url: str = ""
    title: str = ""
    is_authenticated: bool = False
    username: str = ""
    balance_eur: str = ""
    balance_bfs: str = ""
    in_game: str = ""


class BrowserManager:
    """Singleton-ish manager: one browser, one context, one active page."""

    def __init__(self) -> None:
        self._pw: Playwright | None = None
        self._browser: Browser | None = None
        self._ctx: BrowserContext | None = None
        self._page: Page | None = None
        self._started = False

    # ── lifecycle ─────────────────────────────────────────────────────

    async def start(self) -> None:
        if self._started:
            return
        self._pw = await async_playwright().start()
        self._browser = await self._pw.chromium.launch(headless=True)
        self._ctx = await self._browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent=UA,
        )
        await self._load_cookies()
        self._page = await self._ctx.new_page()
        self._started = True
        logger.info("Browser started")

    async def stop(self) -> None:
        if not self._started:
            return
        await self._save_cookies()
        await self._browser.close()  # type: ignore[union-attr]
        await self._pw.stop()  # type: ignore[union-attr]
        self._started = False
        logger.info("Browser stopped")

    @property
    def page(self) -> Page:
        assert self._page is not None, "Browser not started"
        return self._page

    @property
    def context(self) -> BrowserContext:
        assert self._ctx is not None, "Browser not started"
        return self._ctx

    # ── cookie persistence ────────────────────────────────────────────

    async def _save_cookies(self) -> None:
        if self._ctx is None:
            return
        COOKIE_FILE.parent.mkdir(parents=True, exist_ok=True)
        cookies = await self._ctx.cookies()
        COOKIE_FILE.write_text(json.dumps(cookies, ensure_ascii=False, indent=2))
        logger.info("Cookies saved (%d)", len(cookies))

    async def _load_cookies(self) -> None:
        if self._ctx is None or not COOKIE_FILE.exists():
            return
        try:
            cookies = json.loads(COOKIE_FILE.read_text())
            await self._ctx.add_cookies(cookies)
            logger.info("Cookies loaded (%d)", len(cookies))
        except Exception:
            logger.warning("Failed to load cookies", exc_info=True)

    async def persist_cookies(self) -> None:
        await self._save_cookies()

    # ── navigation ────────────────────────────────────────────────────

    async def goto(self, path: str, *, timeout: int = 15000) -> dict[str, Any]:
        url = path if path.startswith("http") else f"{BASE_URL}{path}"
        resp = await self.page.goto(url, wait_until="domcontentloaded", timeout=timeout)
        status = resp.status if resp else 0
        title = await self.page.title()
        return {"url": self.page.url, "status": status, "title": title}

    # ── page state extraction ─────────────────────────────────────────

    async def get_state(self) -> PageState:
        state = PageState(url=self.page.url, title=await self.page.title())
        try:
            info = await self.page.evaluate("""() => {
                const body = document.body.textContent || '';
                const text = body.replace(/\\s+/g, ' ');
                const authMatch = text.match(/(\\w+)\\s+Balance\\s+([\\d.]+)/);
                const bfsMatch = text.match(/BFS\\s+([\\d.]+)/);
                const inGameMatch = text.match(/In game\\s+([\\d.]+)/);
                const hasLogout = !!document.querySelector('a[href="/logout"], .logout');
                return {
                    hasLogout,
                    username: authMatch ? authMatch[1] : '',
                    balanceEur: authMatch ? authMatch[2] : '',
                    bfs: bfsMatch ? bfsMatch[1] : '',
                    inGame: inGameMatch ? inGameMatch[1] : '',
                };
            }""")
            state.is_authenticated = info["hasLogout"]
            state.username = info["username"]
            state.balance_eur = info["balanceEur"]
            state.balance_bfs = info["bfs"]
            state.in_game = info["inGame"]
        except Exception:
            pass
        return state

    # ── auth ──────────────────────────────────────────────────────────

    async def login(self, email: str, password: str) -> PageState:
        await self.goto("/")

        await self.page.evaluate(
            """([email, password]) => {
                const containers = document.querySelectorAll('#login_form');
                for (const c of containers) {
                    const re = c.querySelector('input[name="remail1"]');
                    const rp = c.querySelector('input[name="rassword1"]');
                    if (!re || !rp) continue;
                    re.value = email;
                    rp.value = password;
                    const form = c.querySelector('form.loginForm1');
                    if (form) {
                        form.querySelector('input[name="email"]').value = email;
                        form.querySelector('input[name="password"]').value = password;
                        form.submit();
                        return true;
                    }
                }
                return false;
            }""",
            [email, password],
        )

        await self.page.wait_for_load_state("domcontentloaded")
        await self.page.wait_for_timeout(2000)
        await self._save_cookies()
        return await self.get_state()

    async def logout(self) -> dict[str, str]:
        await self.goto("/logout")
        await self._save_cookies()
        return {"status": "logged_out", "url": self.page.url}

    # ── DOM interaction ───────────────────────────────────────────────

    async def get_text(self, selector: str = "body") -> str:
        el = self.page.locator(selector).first
        raw = await el.text_content() or ""
        return " ".join(raw.split())

    async def get_html(self, selector: str = "#row-content") -> str:
        try:
            return await self.page.locator(selector).first.inner_html()
        except Exception:
            return await self.page.content()

    async def fill(self, selector: str, value: str, *, force: bool = False) -> str:
        loc = self.page.locator(selector).first
        if force:
            await loc.evaluate(f'(el) => el.value = "{value}"')
        else:
            await loc.fill(value)
        return f"Filled {selector} = {value}"

    async def click(self, selector: str, *, force: bool = False) -> str:
        await self.page.locator(selector).first.click(force=force)
        await self.page.wait_for_timeout(1000)
        return f"Clicked {selector}, now at {self.page.url}"

    async def select(self, selector: str, value: str) -> str:
        await self.page.select_option(selector, value)
        return f"Selected {value} in {selector}"

    async def screenshot(self, full_page: bool = False) -> str:
        buf = await self.page.screenshot(full_page=full_page)
        return base64.b64encode(buf).decode()

    async def evaluate(self, js: str) -> Any:
        return await self.page.evaluate(js)

    async def wait(self, ms: int = 2000) -> str:
        await self.page.wait_for_timeout(ms)
        return f"Waited {ms}ms"

    # ── BFS domain helpers ────────────────────────────────────────────

    async def list_sports(self) -> list[dict[str, str]]:
        await self.goto("/")
        return await self.page.evaluate("""() => {
            const links = document.querySelectorAll('a[href]');
            const sports = [];
            const seen = new Set();
            for (const a of links) {
                const h = a.getAttribute('href');
                if (h && h.startsWith('/') && !h.startsWith('/static') &&
                    !h.startsWith('/en/') && !h.startsWith('/de/') && !h.startsWith('/ru/') &&
                    !['/', '/fullRegistration', '/recoverPassword', '/paymentmethods',
                      '/profile', '/logout'].includes(h) &&
                    h.split('/').length >= 3 && !seen.has(h)) {
                    seen.add(h);
                    const text = a.textContent.trim().replace(/\\s+/g, ' ');
                    sports.push({path: h, label: text || h});
                }
            }
            return sports;
        }""")

    async def get_coupon_details(self, path: str) -> dict[str, Any]:
        await self.goto(path)
        await self.page.wait_for_timeout(2000)

        return await self.page.evaluate("""() => {
            const title = document.title;
            const tables = document.querySelectorAll('table');
            const tableData = [];
            for (const t of tables) {
                const rows = [];
                for (const tr of t.querySelectorAll('tr')) {
                    const cells = [];
                    for (const td of tr.querySelectorAll('td, th')) {
                        cells.push(td.textContent.trim().replace(/\\s+/g, ' '));
                    }
                    if (cells.length) rows.push(cells);
                }
                if (rows.length) tableData.push(rows);
            }

            const forms = [];
            for (const f of document.querySelectorAll('#row-content form')) {
                const inputs = [];
                for (const el of f.elements) {
                    if (el.name) {
                        inputs.push({
                            name: el.name, type: el.type,
                            value: el.value?.substring(0, 50) || ''
                        });
                    }
                }
                if (inputs.length) {
                    forms.push({
                        id: f.id, action: f.action, method: f.method,
                        inputs
                    });
                }
            }

            const bodyText = document.querySelector('#row-content')?.textContent || '';
            const text = bodyText.replace(/\\s+/g, ' ').substring(0, 3000);

            return {title, tables: tableData, forms, text};
        }""")
