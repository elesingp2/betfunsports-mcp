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
COOKIE_PATH = Path.home() / ".bfs-mcp" / "cookies.json"
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
        COOKIE_PATH.parent.mkdir(parents=True, exist_ok=True)
        COOKIE_PATH.write_text(json.dumps(await self._ctx.cookies(), ensure_ascii=False, indent=2))

    async def _load_cookies(self) -> None:
        if not self._ctx or not COOKIE_PATH.exists():
            return
        try:
            await self._ctx.add_cookies(json.loads(COOKIE_PATH.read_text()))
        except Exception:
            log.warning("cookie load failed", exc_info=True)

    # ── navigation ────────────────────────────────────────────────────

    async def goto(self, path: str, *, timeout: int = 15_000) -> dict[str, Any]:
        url = path if path.startswith("http") else f"{BASE_URL}{path}"
        resp = await self.page.goto(url, wait_until="domcontentloaded", timeout=timeout)
        return {"url": self.page.url, "status": resp.status if resp else 0, "title": await self.page.title()}

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
        # Check if already authenticated
        s = await self.state()
        if s.authenticated:
            return {**s.to_dict(), "message": "already logged in"}

        await self.page.evaluate(
            """([e, p]) => {
                for (const c of document.querySelectorAll('#login_form')) {
                    const re = c.querySelector('[name="remail1"]');
                    const rp = c.querySelector('[name="rassword1"]');
                    if (!re||!rp) continue;
                    re.value=e; rp.value=p;
                    const f = c.querySelector('form.loginForm1');
                    if (f) { f.querySelector('[name="email"]').value=e; f.querySelector('[name="password"]').value=p; f.submit(); return; }
                }
            }""",
            [email, password],
        )
        await self.page.wait_for_load_state("domcontentloaded")
        await self.page.wait_for_timeout(2000)

        # Check for flash error (e.g. "Player already logged in")
        flash = await self.page.evaluate("""() => {
            const c = document.cookie;
            const m = c.match(/PLAY_FLASH=([^;]+)/);
            return m ? decodeURIComponent(m[1]) : '';
        }""")

        await self._save_cookies()
        s = await self.state()
        result = s.to_dict()
        if flash:
            result["error"] = flash
        if not s.authenticated and not flash:
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

        # Fill visible fields
        await self.page.fill("#oldUame", username)
        await self.page.fill("#oail", email)
        await self.page.fill("#password0", password)
        await self.page.fill("#password2", password)
        await self.page.fill("#firstName", first_name)
        await self.page.fill("#lastName", last_name)
        await self.page.fill("#fbirthDate", birth_date)
        await self.page.fill("#phone", phone)
        await self.page.select_option("#countryCode", country_code)

        if city:
            await self.page.fill("#cityName", city)
        if address:
            await self.page.fill("#addressLine1", address)
        if zip_code:
            await self.page.fill("#zipCode", zip_code)

        if sex == "female":
            await self.page.click("#sex_female", force=True)

        # Accept terms
        cb = self.page.locator("#fform_registration input[type='checkbox']")
        for i in range(await cb.count()):
            if not await cb.nth(i).is_checked():
                await cb.nth(i).check(force=True)

        # Fill honeypot hidden fields via JS
        await self.page.evaluate(f"""() => {{
            const f = document.getElementById('fform_registration');
            if (!f) return;
            const h = (id, val) => {{ const e = f.querySelector('#'+id); if(e) e.value = val; }};
            h('username', {json.dumps(username)});
            h('email', {json.dumps(email)});
            h('password', {json.dumps(password)});
        }}""")

        # Submit
        btn = self.page.locator('#fform_registration button[type="submit"], #fform_registration input[type="submit"]')
        if await btn.count() > 0:
            await btn.first.click(force=True)
        else:
            await self.page.evaluate("document.getElementById('fform_registration').submit()")

        await self.page.wait_for_timeout(3000)

        txt = await self.text("#row-content")
        url = self.page.url
        errors = await self.page.locator("label.error, .alert-danger, .error-message").all_text_contents()
        errors = [e.strip() for e in errors if e.strip()]

        success = any(kw in txt.lower() for kw in ["success", "welcome", "confirm", "verify", "email sent", "registered", "thank"])

        return {
            "success": success,
            "url": url,
            "errors": errors or None,
            "page_text": txt[:500],
        }

    # ── monitoring ────────────────────────────────────────────────────

    async def active_bets(self) -> dict[str, Any]:
        """Get currently active (unresolved) bets."""
        await self.goto("/user/bets")
        await self.page.wait_for_timeout(3000)
        return await self._scrape_bet_table()

    async def _scrape_bet_table(self) -> dict[str, Any]:
        title = await self.page.title()
        if "registration" in title.lower() or "error" in title.lower():
            return {"error": "not authenticated", "title": title}
        return await self.page.evaluate("""() => {
            const t = document.querySelector('#row-content table');
            if (!t) return {headers: [], rows: [], count: 0};
            const h = Array.from(t.querySelectorAll('thead th')).map(th=>th.textContent.trim()).filter(x=>x);
            const r = [];
            t.querySelectorAll('tbody tr').forEach(tr => {
                const c = Array.from(tr.querySelectorAll('td')).map(td=>td.textContent.trim().replace(/\\s+/g,' ')).filter(x=>x);
                if(c.length) r.push(c);
            });
            let csv = h.join(',')+'\\n';
            r.forEach(row => csv += row.map(c=>'"'+c.replace(/"/g,'""')+'"').join(',')+'\\n');
            return {headers: h, rows: r, count: r.length, csv};
        }""")

    # ── DOM helpers ───────────────────────────────────────────────────

    async def text(self, selector: str = "body") -> str:
        raw = await self.page.locator(selector).first.text_content() or ""
        return " ".join(raw.split())

    async def html(self, selector: str = "#row-content") -> str:
        try:
            return await self.page.locator(selector).first.inner_html()
        except Exception:
            return await self.page.content()

    async def fill(self, selector: str, value: str, *, force: bool = False) -> str:
        loc = self.page.locator(selector).first
        if force:
            await loc.evaluate(f'el => el.value = {json.dumps(value)}')
        else:
            await loc.fill(value)
        return f"filled {selector}"

    async def click(self, selector: str, *, force: bool = False) -> str:
        await self.page.locator(selector).first.click(force=force)
        await self.page.wait_for_timeout(1000)
        return f"clicked {selector}"

    async def select(self, selector: str, value: str) -> str:
        await self.page.select_option(selector, value)
        return f"selected {value}"

    async def screenshot(self, full_page: bool = False) -> str:
        return base64.b64encode(await self.page.screenshot(full_page=full_page)).decode()

    async def screenshot_bytes(self, full_page: bool = False) -> bytes:
        return await self.page.screenshot(full_page=full_page)

    async def evaluate(self, js: str) -> Any:
        return await self.page.evaluate(js)

    async def wait(self, ms: int = 2000) -> None:
        await self.page.wait_for_timeout(ms)

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
        ok = any(k in txt.lower() for k in ["accepted", "placed", "принята", "успешно", "thank you", "спасибо"])
        return {"success": ok, "room": room["label"], "stake": stake or room["currentStake"],
                "selections": selections, "page_text": txt[:800]}

    async def forms(self) -> list[dict]:
        return await self.page.evaluate("""()=>
            Array.from(document.forms).map(f=>({
                id:f.id||null,action:f.action,method:f.method,
                fields:Array.from(f.elements).filter(e=>e.name).map(e=>({
                    name:e.name,type:e.type,value:(e.value||'').substring(0,50),
                    visible:e.offsetParent!==null,
                    options:e.tagName==='SELECT'?Array.from(e.options).slice(0,10).map(o=>o.value):undefined
                }))
            })).filter(f=>f.fields.length)
        """)

    async def links(self, pattern: str = "") -> list[dict]:
        return await self.page.evaluate(f"""()=>{{
            const p="{pattern}";
            return Array.from(document.querySelectorAll('a[href]'))
                .map(a=>({{href:a.getAttribute('href'),text:a.textContent.trim().replace(/\\s+/g,' ').substring(0,80)}}))
                .filter(l=>l.href&&!l.href.startsWith('/static')&&(!p||l.href.includes(p)))
                .filter((v,i,a)=>a.findIndex(x=>x.href===v.href)===i).slice(0,50);
        }}""")

    async def bet_history(self) -> dict[str, Any]:
        """Scrape bet history table and return as structured data + CSV."""
        await self.goto("/user/bets/archive")
        await self.page.wait_for_timeout(3000)

        data = await self.page.evaluate("""() => {
            const table = document.querySelector('#row-content table, .dataTable, table');
            if (!table) return {rows: [], csv: '', error: 'no table found'};
            const rawH = Array.from(table.querySelectorAll('thead th')).map(th => th.textContent.trim());
            const headers = rawH.filter(h => h);
            const rows = [];
            table.querySelectorAll('tbody tr').forEach(tr => {
                const rawCells = Array.from(tr.querySelectorAll('td')).map(td => td.textContent.trim().replace(/\\s+/g, ' '));
                const cells = rawCells.filter(c => c);
                if (cells.length) rows.push(cells);
            });
            let csv = headers.join(',') + '\\n';
            rows.forEach(r => csv += r.map(c => '"' + c.replace(/"/g, '""') + '"').join(',') + '\\n');
            return {headers, rows, csv, count: rows.length};
        }""")
        return data

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
