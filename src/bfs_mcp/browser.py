"""Headless browser engine for betfunsports.com."""

from __future__ import annotations

import base64
import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from playwright.async_api import Browser, BrowserContext, Page, Playwright, async_playwright

log = logging.getLogger(__name__)

BASE_URL = "https://betfunsports.com"
DATA_DIR = Path.home() / ".bfs-mcp"
COOKIE_PATH = DATA_DIR / "cookies.json"
CREDS_PATH = DATA_DIR / "credentials.json"
UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)


@dataclass
class State:
    url: str = ""
    title: str = ""
    authenticated: bool = False
    username: str = ""
    balance_eur: str = ""
    balance_bfs: str = ""
    in_game: str = ""

    def to_dict(self) -> dict[str, Any]:
        return self.__dict__


class BFSBrowser:
    """One browser, one context, one page — persistent across calls."""

    def __init__(self) -> None:
        self._pw: Playwright | None = None
        self._browser: Browser | None = None
        self._ctx: BrowserContext | None = None
        self._page: Page | None = None

    @property
    def ready(self) -> bool:
        return self._page is not None

    @property
    def page(self) -> Page:
        if self._page is None:
            raise RuntimeError("Browser not started — call start() first")
        return self._page

    # ── lifecycle ─────────────────────────────────────────────────────

    async def start(self) -> None:
        if self.ready:
            return
        self._pw = await async_playwright().start()
        self._browser = await self._pw.chromium.launch(headless=True)
        self._ctx = await self._browser.new_context(viewport={"width": 1920, "height": 1080}, user_agent=UA)
        await self._load_cookies()
        self._page = await self._ctx.new_page()
        log.info("browser started")

    async def stop(self) -> None:
        if not self.ready:
            return
        await self._save_cookies()
        if self._browser:
            await self._browser.close()
        if self._pw:
            await self._pw.stop()
        self._page = None
        log.info("browser stopped")

    async def _save_cookies(self) -> None:
        if not self._ctx:
            return
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        COOKIE_PATH.write_text(json.dumps(await self._ctx.cookies(), ensure_ascii=False, indent=2))

    async def _load_cookies(self) -> None:
        if not self._ctx or not COOKIE_PATH.exists():
            return
        try:
            await self._ctx.add_cookies(json.loads(COOKIE_PATH.read_text()))
        except Exception:
            log.warning("cookie load failed", exc_info=True)

    # ── credentials ───────────────────────────────────────────────────

    @staticmethod
    def save_credentials(email: str, password: str) -> None:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        CREDS_PATH.write_text(json.dumps({"email": email, "password": password}))
        log.info("credentials saved to %s", CREDS_PATH)

    @staticmethod
    def load_credentials() -> dict[str, str] | None:
        if not CREDS_PATH.exists():
            return None
        try:
            data = json.loads(CREDS_PATH.read_text())
            if data.get("email") and data.get("password"):
                return data
        except Exception:
            pass
        return None

    # ── navigation ────────────────────────────────────────────────────

    async def goto(self, path: str, *, timeout: int = 15_000) -> dict[str, Any]:
        url = path if path.startswith("http") else f"{BASE_URL}{path}"
        try:
            resp = await self.page.goto(url, wait_until="domcontentloaded", timeout=timeout)
            return {"url": self.page.url, "status": resp.status if resp else 0, "title": await self.page.title()}
        except Exception as exc:
            if "ERR_ABORTED" in str(exc):
                log.warning("goto %s aborted (likely redirect) — waiting for page to settle", url)
                try:
                    await self.page.wait_for_load_state("domcontentloaded", timeout=timeout)
                except Exception:
                    pass
                await self.page.wait_for_timeout(2000)
                return {"url": self.page.url, "status": 0, "title": await self.page.title(), "warning": "ERR_ABORTED — page may have redirected"}
            raise

    async def state(self) -> State:
        s = State(url=self.page.url, title=await self.page.title())
        try:
            info = await self.page.evaluate("""() => {
                const t = (document.body.textContent||'').replace(/\\s+/g,' ');
                const a = t.match(/(\\w+)\\s+Balance\\s+([\\d.]+)/);
                const b = t.match(/BFS\\s+([\\d.]+)/);
                const g = t.match(/In game\\s+([\\d.]+)/);
                return {
                    auth: !!document.querySelector('a[href="/logout"],.logout'),
                    user: a?a[1]:'', eur: a?a[2]:'', bfs: b?b[1]:'', game: g?g[1]:''
                };
            }""")
            s.authenticated = info["auth"]
            s.username = info["user"]
            s.balance_eur = info["eur"]
            s.balance_bfs = info["bfs"]
            s.in_game = info["game"]
        except Exception:
            pass
        return s

    # ── auth ──────────────────────────────────────────────────────────

    async def login(self, email: str, password: str) -> dict[str, Any]:
        await self.goto("/")
        s = await self.state()
        if s.authenticated:
            return {**s.to_dict(), "message": "already logged in"}

        result = await self._submit_login(email, password)

        if not result.get("authenticated") and "already logged" in result.get("error", "").lower():
            log.info("session conflict — logging out and retrying")
            await self.logout()
            await self.goto("/")
            result = await self._submit_login(email, password)

        if result.get("authenticated"):
            self.save_credentials(email, password)

        return result

    async def _submit_login(self, email: str, password: str) -> dict[str, Any]:
        await self.page.evaluate(
            """([e, p]) => {
                for (const c of document.querySelectorAll('#login_form')) {
                    const re = c.querySelector('[name="remail1"]');
                    const rp = c.querySelector('[name="rassword1"]');
                    if (!re||!rp) continue;
                    re.value=e; rp.value=p;
                    const f = c.querySelector('form.loginForm1');
                    if (f) {
                        const ei = f.querySelector('[name="email"]');
                        const pi = f.querySelector('[name="password"]');
                        if(ei) ei.value=e; if(pi) pi.value=p;
                    }
                }
            }""",
            [email, password],
        )

        try:
            async with self.page.expect_navigation(wait_until="domcontentloaded", timeout=15_000):
                await self.page.evaluate(
                    """() => {
                        for (const c of document.querySelectorAll('#login_form')) {
                            if (c.offsetParent === null) continue;
                            const f = c.querySelector('form.loginForm1');
                            if (f) { f.submit(); return true; }
                        }
                        return false;
                    }"""
                )
        except Exception:
            pass

        await self.page.wait_for_timeout(3000)

        error = ""
        try:
            error = await self.page.evaluate("""() => {
                const body = (document.body.textContent || '').replace(/\\s+/g, ' ');
                if (/player already logged/i.test(body)) return 'Player already logged in';
                if (/login failed/i.test(body)) return 'Login failed';
                const flash = (document.cookie.match(/PLAY_FLASH=([^;]+)/) || [])[1];
                if (flash) return decodeURIComponent(flash);
                const modal = document.querySelector('.modal.show, .modal-dialog, .alert-danger, .swal2-popup');
                if (modal) {
                    const t = modal.textContent.trim();
                    if (t) return t.substring(0, 200);
                }
                return '';
            }""")
        except Exception:
            log.warning("could not read login error", exc_info=True)

        await self._save_cookies()
        s = await self.state()
        result = s.to_dict()
        if error:
            result["error"] = error
        if not s.authenticated and not error:
            result["error"] = "login failed — check credentials"
        return result

    async def logout(self) -> dict[str, str]:
        await self.goto("/logout")
        await self._save_cookies()
        return {"status": "ok", "url": self.page.url}

    async def register(self, username: str, email: str, password: str,
                       first_name: str, last_name: str, birth_date: str,
                       phone: str, country_code: str = "US",
                       city: str = "", address: str = "", zip_code: str = "",
                       sex: str = "male") -> dict[str, Any]:
        """Register a new account. birth_date format: DD/MM/YYYY."""
        await self.goto("/fullRegistration")
        await self.page.wait_for_timeout(1000)

        form_exists = await self.page.locator("#fform_registration").count() > 0
        if not form_exists:
            return {"success": False, "error": "registration form not found (may be logged in)"}

        await self.page.fill("#oldUame", username)
        await self.page.fill("#oail", email)
        await self.page.fill("#password0", password)
        await self.page.fill("#password2", password)
        await self.page.fill("#firstName", first_name)
        await self.page.fill("#lastName", last_name)

        await self.page.evaluate(
            f'document.getElementById("fbirthDate").value = {json.dumps(birth_date)}'
        )

        await self.page.fill("#phone", phone)
        await self.page.select_option("#countryCode", country_code)

        await self.page.fill("#cityName", city or "-")
        await self.page.fill("#addressLine1", address or "-")
        await self.page.evaluate(
            f'document.getElementById("zipCode").value = {json.dumps(zip_code or "00000")}'
        )

        if sex == "female":
            await self.page.click("#sex_female", force=True)

        cb = self.page.locator("#fform_registration input[type='checkbox']")
        for i in range(await cb.count()):
            if not await cb.nth(i).is_checked():
                await cb.nth(i).check(force=True)

        await self.page.evaluate(f"""() => {{
            const f = document.getElementById('fform_registration');
            if (!f) return;
            const h = (id, val) => {{
                const e = f.querySelector('#'+id);
                if (!e) return;
                e.removeAttribute('maxlength');
                e.value = val;
            }};
            h('username', {json.dumps(username)});
            h('email', {json.dumps(email)});
            h('password', {json.dumps(password)});
        }}""")

        initial_url = self.page.url
        btn = self.page.locator('#fform_registration button[type="submit"], #fform_registration input[type="submit"]')
        if await btn.count() > 0:
            await btn.first.click(force=True)
        else:
            await self.page.evaluate("document.getElementById('fform_registration').submit()")

        await self.page.wait_for_timeout(4000)

        new_url = self.page.url
        txt = await self.text("#row-content")
        errors = await self.page.locator("label.error, .alert-danger, .error-message").all_text_contents()
        errors = [e.strip() for e in errors if e.strip()]

        navigated = new_url != initial_url
        low = txt.lower()
        success_keywords = ["success", "welcome", "email sent", "registered",
                            "thank", "verify your email", "check your email",
                            "confirmation link", "finishing registration", "confirmation email"]
        has_keyword = any(kw in low for kw in success_keywords)
        still_on_form = "join the club" in low or "/fullRegistration" in new_url

        success = (has_keyword or navigated) and not still_on_form
        needs_confirmation = any(kw in low for kw in
                                 ["confirmation email", "finishing registration",
                                  "verify your email", "check your email"])

        mailbox_link = await self.page.evaluate("""() => {
            const a = document.querySelector('#row-content a[href*="mail"]');
            return a ? a.href : null;
        }""")

        if success:
            self.save_credentials(email, password)

        result: dict[str, Any] = {
            "success": success,
            "url": new_url,
            "errors": errors or None,
            "page_text": txt[:800],
        }
        if needs_confirmation:
            result["needs_email_confirmation"] = True
            result["message"] = "Check your inbox and click the confirmation link to activate the account."
            if mailbox_link:
                result["mailbox_link"] = mailbox_link
        return result

    async def confirm_registration(self, confirmation_url: str) -> dict[str, Any]:
        """Visit an email confirmation link to activate a registered account."""
        if not confirmation_url.startswith("http"):
            confirmation_url = f"{BASE_URL}{confirmation_url}"

        resp = await self.page.goto(confirmation_url, wait_until="domcontentloaded", timeout=15_000)
        await self.page.wait_for_timeout(3000)

        url = self.page.url
        txt = await self.text("#row-content")
        low = txt.lower()

        confirmed = any(kw in low for kw in
                        ["confirmed", "activated", "success", "welcome"])
        s = await self.state()

        return {
            "confirmed": confirmed or s.authenticated,
            "authenticated": s.authenticated,
            "url": url,
            "status": resp.status if resp else 0,
            "page_text": txt[:800],
        }

    # ── monitoring ────────────────────────────────────────────────────

    async def active_bets(self) -> str:
        """Get currently active (unresolved) bets as formatted text."""
        await self._goto_user_page("/user/bets")
        return await self._format_bet_table("Active bets")

    async def _goto_user_page(self, path: str) -> None:
        """Navigate to a /user/* page, retrying via JS if page.goto gets aborted."""
        target = f"{BASE_URL}{path}"
        result = await self.goto(path)
        current = self.page.url.rstrip("/")
        expected = target.rstrip("/")

        if current == expected:
            await self.page.wait_for_timeout(2000)
            return

        log.warning("goto landed on %s instead of %s — retrying via JS", current, expected)
        await self.page.evaluate(f"window.location.href = {json.dumps(target)}")
        try:
            await self.page.wait_for_load_state("domcontentloaded", timeout=15_000)
        except Exception:
            pass
        await self.page.wait_for_timeout(3000)

        final = self.page.url.rstrip("/")
        if final != expected:
            log.warning("JS navigation landed on %s instead of %s", final, expected)

    async def _format_bet_table(self, title_label: str) -> str:
        title = await self.page.title()
        url = self.page.url
        if "registration" in title.lower() or "error" in title.lower():
            return f"Error: not authenticated. Please login first. (url={url})"
        data = await self.page.evaluate("""() => {
            const selectors = ['#row-content table', 'table.table', 'table'];
            for (const sel of selectors) {
                const t = document.querySelector(sel);
                if (!t) continue;
                const h = Array.from(t.querySelectorAll('thead th, tr:first-child th'))
                    .map(th => th.textContent.trim()).filter(x => x);
                const r = [];
                const bodyRows = t.querySelectorAll('tbody tr');
                (bodyRows.length ? bodyRows : t.querySelectorAll('tr:not(:first-child)')).forEach(tr => {
                    const c = Array.from(tr.querySelectorAll('td'))
                        .map(td => td.textContent.trim().replace(/\\s+/g, ' ')).filter(x => x);
                    if (c.length) r.push(c);
                });
                if (r.length) return {headers: h, rows: r};
            }
            const ct = (document.querySelector('#row-content') || document.body)
                .textContent.replace(/\\s+/g, ' ').trim();
            return {headers: [], rows: [], page_text: ct.substring(0, 2000)};
        }""")
        headers = data.get("headers", [])
        rows = data.get("rows", [])
        if not rows:
            page_text = data.get("page_text", "")
            return f"{title_label}: none found.\nURL: {url}\nPage content: {page_text[:1500]}"
        lines = [f"{title_label} ({len(rows)}):", ""]
        for i, row in enumerate(rows, 1):
            parts = []
            for h, v in zip(headers, row):
                if h == "-":
                    continue
                parts.append(f"{h}: {v}")
            lines.append(f"  {i}. " + " | ".join(parts))
        return "\n".join(lines)

    async def bet_history(self) -> str:
        """Scrape bet history and return as formatted text."""
        await self._goto_user_page("/user/bets/archive")
        return await self._format_bet_table("Bet history")

    # ── DOM helpers ───────────────────────────────────────────────────

    async def text(self, selector: str = "body") -> str:
        raw = await self.page.locator(selector).first.text_content() or ""
        return " ".join(raw.split())

    async def screenshot_bytes(self, full_page: bool = False, timeout: int = 15_000) -> bytes:
        try:
            await self.page.wait_for_load_state("domcontentloaded", timeout=5_000)
        except Exception:
            pass

        try:
            return await self.page.screenshot(full_page=full_page, timeout=timeout)
        except Exception:
            if full_page:
                log.warning("full-page screenshot failed, retrying viewport-only")
                return await self.page.screenshot(full_page=False, timeout=timeout)
            raise

    async def evaluate(self, js: str) -> Any:
        return await self.page.evaluate(js)

    # ── BFS domain ────────────────────────────────────────────────────

    async def list_sports(self) -> list[dict[str, str]]:
        await self.goto("/")
        return await self.page.evaluate("""() => {
            const seen=new Set(), out=[];
            document.querySelectorAll('a[href]').forEach(a=>{
                const h=a.getAttribute('href');
                if(h&&h.startsWith('/')&&!h.startsWith('/static')&&!h.startsWith('/en/')&&!h.startsWith('/de/')&&!h.startsWith('/ru/')&&!h.startsWith('/user/')&&!h.startsWith('/deposit/')&&!h.startsWith('/withdrawal/')
                  &&!['/','fullRegistration','recoverPassword','paymentmethods','profile','logout'].some(x=>h==='/'+x||h===x)
                  &&h.split('/').length>=3&&!seen.has(h)){
                    seen.add(h);
                    out.push({path:h, label:a.textContent.trim().replace(/\\s+/g,' ').substring(0,80)});
                }
            });
            return out;
        }""")

    async def bet_info(self, path: str) -> dict[str, Any]:
        await self.goto(path)
        await self.page.wait_for_timeout(2000)
        return await self.page.evaluate("""() => {
            const title=document.title, c=document.querySelector('#row-content');
            if(!c) return {title, error:'no content', events:[], rooms:[]};
            const t=c.textContent.replace(/\\s+/g,' ').trim();
            if(t.includes('Bets are not possible')||t.includes('event has begun'))
                return {title, error:'betting closed', events:[], rooms:[], text:t.substring(0,500)};
            const f=document.querySelector('form.coupon-form');
            if(!f) return {title, error:'no bet form', events:[], rooms:[], text:t.substring(0,500)};
            const cid=f.action.match(/\\/save\\/(\\d+)/)?.[1]||'';
            const em={};
            f.querySelectorAll('input.coupon-checkbox').forEach(cb=>{
                const m=cb.name.match(/ololo\\[(\\d+)\\]\\[(\\d+)\\]/);
                if(!m)return;
                const[_,eid,oc]=m;
                if(!em[eid])em[eid]={eventId:eid,outcomes:[]};
                em[eid].outcomes.push({code:oc,label:{8:'1 (home)',9:'X (draw)',10:'2 (away)'}[oc]||oc,checked:cb.checked});
            });
            const rooms=[];
            let ri=0;
            const labels=['Wooden (TOT)','Bronze (EUR)','Silver (EUR)','Golden (EUR)'];
            f.querySelectorAll('input.stake-input').forEach(inp=>{
                const rid=inp.id.replace('stake-','');
                rooms.push({roomId:rid, label:labels[ri]||'Room '+ri, stakeSelector:'#stake-'+rid,
                    submitSelector:'input[name="pool-'+rid+'"]', currentStake:inp.value});
                ri++;
            });
            return {title, couponId:cid, events:Object.values(em), rooms, text:t.substring(0,1500)};
        }""")

    async def place_bet(self, coupon_path: str, selections: dict[str, str],
                        room_index: int = 0, stake: str | None = None) -> dict[str, Any]:
        info = await self.bet_info(coupon_path)
        if info.get("error"):
            return {"success": False, "error": info["error"]}
        if not info.get("rooms"):
            return {"success": False, "error": "no rooms"}
        if room_index >= len(info["rooms"]):
            return {"success": False, "error": f"room {room_index} not found"}
        room = info["rooms"][room_index]
        for eid, oc in selections.items():
            await self.page.evaluate(
                f'()=>{{const cb=document.querySelector(\'input.coupon-checkbox[name="ololo[{eid}][{oc}]"]\');'
                f'if(cb){{cb.checked=true;cb.dispatchEvent(new Event("change",{{bubbles:true}}));}}}}'
            )
        if stake:
            await self.page.evaluate(
                f'()=>{{const i=document.querySelector(\'{room["stakeSelector"]}\');'
                f'if(i){{i.value="{stake}";i.dispatchEvent(new Event("change",{{bubbles:true}}));}}}}'
            )
        await self.page.locator(room["submitSelector"]).click(force=True)
        await self.page.wait_for_timeout(3000)
        txt = await self.text("#row-content")
        ok = any(k in txt.lower() for k in ["accepted", "placed", "thank you"])
        return {"success": ok, "room": room["label"], "stake": stake or room["currentStake"],
                "selections": selections, "page_text": txt[:800]}

    async def account_info(self) -> dict[str, Any]:
        """Get full account details."""
        await self.goto("/user/details")
        await self.page.wait_for_timeout(2000)
        return await self.page.evaluate("""() => {
            const c = document.querySelector('#row-content');
            if (!c) return {error: 'no content'};
            const text = c.textContent.replace(/\\s+/g, ' ').trim();
            const pairs = {};
            c.querySelectorAll('label, .label, dt').forEach(el => {
                const key = el.textContent.trim().replace(/:$/, '');
                const val = el.nextElementSibling?.textContent?.trim() || '';
                if (key && val) pairs[key] = val;
            });
            return {text: text.substring(0, 1500), fields: pairs};
        }""")
