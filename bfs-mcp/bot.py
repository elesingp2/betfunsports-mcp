#!/usr/bin/env python3
"""
BFS Telegram Bot — async bot that drives betfunsports.com
via headless Playwright. Thin wrapper over BrowserManager.
"""

import asyncio
import io
import base64
import logging
import sys

sys.path.insert(0, "/workspace/bfs-mcp/src")

from aiogram import Bot, Dispatcher, F, Router
from aiogram.types import Message, BufferedInputFile
from aiogram.filters import Command
from aiogram.enums import ParseMode

from bfs_mcp.browser import BrowserManager

TOKEN = "8491424456:AAG0Rlgk6JoQrdefcSjRPX_jppRWns8naOY"

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("bfs-bot")

bot = Bot(token=TOKEN)
dp = Dispatcher()
router = Router()
dp.include_router(router)

bm = BrowserManager()


# ── helpers ───────────────────────────────────────────────────────────

async def ensure_browser():
    await bm.start()


async def send_screenshot(msg: Message, full: bool = False):
    await ensure_browser()
    b64 = await bm.screenshot(full_page=full)
    img = base64.b64decode(b64)
    photo = BufferedInputFile(img, filename="screenshot.png")
    await msg.answer_photo(photo)


def esc(text: str) -> str:
    """Escape MarkdownV2 special chars."""
    for ch in r"_*[]()~`>#+-=|{}.!":
        text = text.replace(ch, f"\\{ch}")
    return text


# ── commands ──────────────────────────────────────────────────────────

@router.message(Command("start", "help"))
async def cmd_help(msg: Message):
    await msg.answer(
        "<b>BFS Browser Bot</b>\n\n"
        "<b>Auth:</b>\n"
        "/login email password — войти\n"
        "/logout — выйти\n"
        "/state — статус: URL, auth, баланс\n\n"
        "<b>BFS:</b>\n"
        "/balance — баланс EUR + BFS\n"
        "/sports — список видов спорта/купонов\n"
        "/coupon path — детали купона\n"
        "/profile — профиль\n"
        "/payment — платёжные методы\n\n"
        "<b>Browser:</b>\n"
        "/go url — навигация\n"
        "/text [selector] — текст страницы\n"
        "/html [selector] — HTML\n"
        "/screen — скриншот\n"
        "/fullscreen — полный скриншот\n"
        "/click selector — клик\n"
        "/fill selector | value — заполнить поле\n"
        "/js код — выполнить JavaScript\n"
        "/forms — формы на странице\n"
        "/links [фильтр] — ссылки",
        parse_mode=ParseMode.HTML,
    )


@router.message(Command("login"))
async def cmd_login(msg: Message):
    parts = msg.text.split(maxsplit=2)
    if len(parts) < 3:
        await msg.answer("Формат: /login email password")
        return
    email, password = parts[1], parts[2]
    await ensure_browser()
    status = await msg.answer("⏳ Логинюсь...")
    state = await bm.login(email, password)
    if state.is_authenticated:
        await status.edit_text(
            f"✅ Залогинен: <b>{state.username}</b>\n"
            f"💶 {state.balance_eur} EUR | 🎮 BFS {state.balance_bfs}\n"
            f"🎯 In game: {state.in_game} EUR",
            parse_mode=ParseMode.HTML,
        )
    else:
        await status.edit_text("❌ Не удалось войти. Возможно, сессия уже активна в браузере.")
    await send_screenshot(msg)


@router.message(Command("logout"))
async def cmd_logout(msg: Message):
    await ensure_browser()
    result = await bm.logout()
    await msg.answer(f"Вышел. URL: {result['url']}")


@router.message(Command("state"))
async def cmd_state(msg: Message):
    await ensure_browser()
    s = await bm.get_state()
    auth = "✅ да" if s.is_authenticated else "❌ нет"
    await msg.answer(
        f"<b>Состояние</b>\n"
        f"URL: {esc(s.url)}\n"
        f"Title: {esc(s.title)}\n"
        f"Auth: {auth}\n"
        f"User: {s.username or '—'}\n"
        f"EUR: {s.balance_eur or '—'}\n"
        f"BFS: {s.balance_bfs or '—'}\n"
        f"In game: {s.in_game or '—'}",
        parse_mode=ParseMode.HTML,
    )


@router.message(Command("balance"))
async def cmd_balance(msg: Message):
    await ensure_browser()
    await bm.goto("/")
    s = await bm.get_state()
    if not s.is_authenticated:
        await msg.answer("Не залогинен. Используй /login email password")
        return
    await msg.answer(
        f"👤 {s.username}\n💶 {s.balance_eur} EUR\n🎮 {s.balance_bfs} BFS\n🎯 In game: {s.in_game} EUR",
    )


@router.message(Command("sports"))
async def cmd_sports(msg: Message):
    await ensure_browser()
    status = await msg.answer("⏳ Загружаю...")
    sports = await bm.list_sports()
    lines = [f"<b>Спорт / купоны ({len(sports)}):</b>"]
    for s in sports[:30]:
        lines.append(f"• <code>{s['path']}</code> — {esc(s['label'][:60])}")
    await status.edit_text("\n".join(lines), parse_mode=ParseMode.HTML)


@router.message(Command("coupon"))
async def cmd_coupon(msg: Message):
    parts = msg.text.split(maxsplit=1)
    if len(parts) < 2:
        await msg.answer("Формат: /coupon /football/prizecoupons1X2")
        return
    await ensure_browser()
    status = await msg.answer("⏳ Загружаю купон...")
    details = await bm.get_coupon_details(parts[1])
    text = details.get("text", "")[:3000]
    title = details.get("title", "")
    forms_count = len(details.get("forms", []))
    tables_count = len(details.get("tables", []))
    await status.edit_text(
        f"<b>{esc(title)}</b>\n"
        f"Forms: {forms_count} | Tables: {tables_count}\n\n"
        f"{esc(text[:2000])}",
        parse_mode=ParseMode.HTML,
    )
    await send_screenshot(msg)


@router.message(Command("profile"))
async def cmd_profile(msg: Message):
    await ensure_browser()
    nav = await bm.goto("/profile")
    text = await bm.get_text("#row-content")
    await msg.answer(f"<b>{esc(nav['title'])}</b>\n\n{esc(text[:3000])}", parse_mode=ParseMode.HTML)


@router.message(Command("payment"))
async def cmd_payment(msg: Message):
    await ensure_browser()
    nav = await bm.goto("/paymentmethods")
    text = await bm.get_text("#row-content")
    await msg.answer(f"<b>{esc(nav['title'])}</b>\n\n{esc(text[:3000])}", parse_mode=ParseMode.HTML)


@router.message(Command("go"))
async def cmd_go(msg: Message):
    parts = msg.text.split(maxsplit=1)
    if len(parts) < 2:
        await msg.answer("Формат: /go /football/prizecoupons1X2")
        return
    await ensure_browser()
    result = await bm.goto(parts[1])
    await msg.answer(f"→ {result['status']} {result['title']}\n{result['url']}")
    await send_screenshot(msg)


@router.message(Command("text"))
async def cmd_text(msg: Message):
    parts = msg.text.split(maxsplit=1)
    selector = parts[1] if len(parts) > 1 else "#row-content"
    await ensure_browser()
    text = await bm.get_text(selector)
    await msg.answer(text[:4000] or "(пусто)")


@router.message(Command("html"))
async def cmd_html(msg: Message):
    parts = msg.text.split(maxsplit=1)
    selector = parts[1] if len(parts) > 1 else "#row-content"
    await ensure_browser()
    html = await bm.get_html(selector)
    await msg.answer(f"<code>{esc(html[:3500])}</code>", parse_mode=ParseMode.HTML)


@router.message(Command("screen"))
async def cmd_screen(msg: Message):
    await ensure_browser()
    await send_screenshot(msg)


@router.message(Command("fullscreen"))
async def cmd_fullscreen(msg: Message):
    await ensure_browser()
    await send_screenshot(msg, full=True)


@router.message(Command("click"))
async def cmd_click(msg: Message):
    parts = msg.text.split(maxsplit=1)
    if len(parts) < 2:
        await msg.answer("Формат: /click CSS_SELECTOR")
        return
    await ensure_browser()
    result = await bm.click(parts[1], force=True)
    await msg.answer(result)
    await send_screenshot(msg)


@router.message(Command("fill"))
async def cmd_fill(msg: Message):
    parts = msg.text.split(maxsplit=1)
    if len(parts) < 2 or "|" not in parts[1]:
        await msg.answer("Формат: /fill CSS_SELECTOR | значение")
        return
    selector, value = parts[1].split("|", 1)
    await ensure_browser()
    result = await bm.fill(selector.strip(), value.strip(), force=True)
    await msg.answer(result)


@router.message(Command("js"))
async def cmd_js(msg: Message):
    parts = msg.text.split(maxsplit=1)
    if len(parts) < 2:
        await msg.answer("Формат: /js document.title")
        return
    await ensure_browser()
    try:
        result = await bm.evaluate(parts[1])
        text = str(result)
        await msg.answer(f"<code>{esc(text[:3500])}</code>", parse_mode=ParseMode.HTML)
    except Exception as e:
        await msg.answer(f"JS Error: {e}")


@router.message(Command("forms"))
async def cmd_forms(msg: Message):
    await ensure_browser()
    forms = await bm.evaluate("""() => {
        return Array.from(document.forms).map(f => ({
            id: f.id || '(no id)',
            action: f.action,
            method: f.method,
            fields: Array.from(f.elements).filter(e => e.name).map(e =>
                e.name + ':' + e.type + (e.offsetParent ? '' : ' [hidden]')
            ).join(', ')
        })).filter(f => f.fields);
    }""")
    lines = [f"<b>Формы ({len(forms)}):</b>"]
    for f in forms[:10]:
        lines.append(f"\n<b>{esc(f['id'])}</b> → {esc(f['action'][:60])}")
        lines.append(f"<code>{esc(f['fields'][:200])}</code>")
    await msg.answer("\n".join(lines), parse_mode=ParseMode.HTML)


@router.message(Command("links"))
async def cmd_links(msg: Message):
    parts = msg.text.split(maxsplit=1)
    pattern = parts[1] if len(parts) > 1 else ""
    await ensure_browser()
    links = await bm.evaluate(f"""() => {{
        const p = "{pattern}";
        return Array.from(document.querySelectorAll('a[href]'))
            .map(a => ({{h: a.getAttribute('href'), t: a.textContent.trim().replace(/\\s+/g,' ').substring(0,60)}}))
            .filter(l => l.h && l.h.startsWith('/') && !l.h.startsWith('/static') && (!p || l.h.includes(p)))
            .filter((v,i,a) => a.findIndex(x => x.h===v.h)===i).slice(0,30);
    }}""")
    lines = [f"<b>Ссылки ({len(links)}):</b>"]
    for l in links:
        lines.append(f"• <code>{l['h']}</code> — {esc(l['t'][:50])}")
    await msg.answer("\n".join(lines), parse_mode=ParseMode.HTML)


# ── fallback ──────────────────────────────────────────────────────────

@router.message()
async def fallback(msg: Message):
    await msg.answer("Неизвестная команда. /help для списка.")


# ── main ──────────────────────────────────────────────────────────────

async def main():
    log.info("Starting BFS Telegram Bot...")
    await ensure_browser()
    await bm.goto("/")
    log.info("Browser ready, starting polling...")
    try:
        await dp.start_polling(bot)
    finally:
        await bm.stop()


if __name__ == "__main__":
    asyncio.run(main())
