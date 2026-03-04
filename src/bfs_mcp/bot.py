"""BFS Telegram Bot — LLM agent that drives betfunsports.com via headless browser."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import traceback
from typing import Any

from aiogram import Bot, Dispatcher, Router
from aiogram.types import Message, BufferedInputFile
from aiogram.filters import Command
from openai import AsyncOpenAI

from .browser import BFSBrowser

log = logging.getLogger(__name__)

TG_TOKEN = os.environ["BFS_TG_TOKEN"]
LLM_KEY = os.environ["BFS_LLM_KEY"]
LLM_BASE = os.environ.get("BFS_LLM_BASE", "https://openrouter.ai/api/v1")
LLM_MODEL = os.environ.get("BFS_LLM_MODEL", "deepseek/deepseek-chat")
MAX_HISTORY = int(os.environ.get("BFS_MAX_HISTORY", "30"))
MAX_ITER = int(os.environ.get("BFS_MAX_ITER", "8"))

bot = Bot(token=TG_TOKEN)
dp = Dispatcher()
router = Router()
dp.include_router(router)
bm = BFSBrowser()
llm = AsyncOpenAI(base_url=LLM_BASE, api_key=LLM_KEY)
conversations: dict[int, list[dict]] = {}


def _td(name: str, desc: str, props: dict[str, Any] | None = None, req: list[str] | None = None) -> dict:
    schema: dict = {"type": "object", "properties": {}}
    for k, v in (props or {}).items():
        schema["properties"][k] = {"type": v} if isinstance(v, str) else v
    if req:
        schema["required"] = req
    return {"type": "function", "function": {"name": name, "description": desc, "parameters": schema}}


TOOLS = [
    _td("bfs_login",
        "Login to betfunsports.com. Handles honeypot fields automatically. Returns auth state, username, EUR and BFS balances.",
        {"email": "string", "password": "string"}, ["email", "password"]),
    _td("bfs_logout",
        "Logout from betfunsports.com and clear session cookies."),
    _td("bfs_state",
        "Get current page state: URL, page title, whether user is authenticated, username, EUR balance, BFS balance, in-game amount. "
        "ALWAYS call this first to check if user is logged in."),
    _td("bfs_list_sports",
        "Navigate to homepage and list all available sports and coupons. Returns array of {path, label}. "
        "Example paths: /football/prizecoupons1X2, /hockey/kHLRegular, /tennis/atpGenevaOpen."),
    _td("bfs_bet_info",
        "Navigate to a coupon page and parse it into structured betting info. Returns: couponId, events (with eventId and outcome options), "
        "rooms (Wooden/Bronze/Silver/Golden with roomId, stakes, submit selectors), and page text. ALWAYS call this before placing a bet.",
        {"path": {"type": "string", "description": "Coupon path, e.g. /FOOTBALL/spainPrimeraDivision/18638"}}, ["path"]),
    _td("bfs_place_bet",
        "Place a bet on a coupon. Requires login. Selects outcomes, sets stake, submits form. Returns success status and page text after submission.",
        {"coupon_path": {"type": "string", "description": "Full coupon path from bfs_bet_info"},
         "selections": {"type": "object", "description": "Map {eventId: outcomeCode}. For 1X2: '8'=home win(1), '9'=draw(X), '10'=away win(2)",
                        "additionalProperties": {"type": "string"}},
         "room_index": {"type": "integer", "description": "0=Wooden(BFS,free), 1=Bronze(1-5 EUR), 2=Silver(10-50 EUR), 3=Golden(100-500 EUR)", "default": 0},
         "stake": {"type": "string", "description": "Bet amount as string. If empty, uses room default."}},
        ["coupon_path", "selections"]),
    _td("browser_navigate",
        "Navigate to any URL or relative path on betfunsports.com. Returns HTTP status, final URL, page title.",
        {"url": "string"}, ["url"]),
    _td("browser_text",
        "Extract visible text from current page by CSS selector. Use '#row-content' for main content, 'body' for full page.",
        {"selector": {"type": "string", "default": "#row-content"}}),
    _td("browser_click",
        "Click a page element by CSS selector. Force-clicks even hidden elements.",
        {"selector": "string"}, ["selector"]),
    _td("browser_fill",
        "Fill a form input by CSS selector.",
        {"selector": "string", "value": "string"}, ["selector", "value"]),
    _td("browser_select",
        "Select an option in a <select> dropdown by value.",
        {"selector": "string", "value": "string"}, ["selector", "value"]),
    _td("browser_screenshot",
        "Take a PNG screenshot of the current page. Call after navigation, login, or bet placement to show user the result.",
        {"full_page": {"type": "boolean", "default": False}}),
    _td("browser_eval",
        "Execute arbitrary JavaScript in the page context and return the result. Use for complex DOM queries or data extraction.",
        {"javascript": "string"}, ["javascript"]),
    _td("browser_forms",
        "List all HTML forms on the current page with field names, types, values, and visibility. Useful to understand page structure before interaction."),
    _td("browser_links",
        "List all links on the current page. Optional substring filter on href.",
        {"filter_pattern": {"type": "string", "default": ""}}),
    _td("browser_wait",
        "Wait N milliseconds for dynamic content to load.",
        {"ms": {"type": "integer", "default": 2000}}),
]

SYSTEM = """Ты — AI-агент, управляющий сайтом betfunsports.com через headless-браузер Playwright.
Ты ОБЯЗАН использовать доступные tool calls для взаимодействия с сайтом. НЕ ВЫДУМЫВАЙ что инструменты недоступны — они все работают.

## О системе Betfunsports (TOTUP)

Betfunsports — P2P система спортивных прогнозов. Ставки игроков формируют призовой пул, который полностью распределяется между победителями.

**Ключевые правила:**
- 50% ставок выигрывают (по точности прогноза)
- Точность прогноза оценивается от 0 до 100 баллов
- Выигрыш пропорционален точности × размеру ставки
- Минимальный коэффициент выигрыша: 1.3

**4 стола (rooms):**
- Wooden (index=0) — BFS (виртуальная валюта, бесплатно), 1-10 BFS
- Bronze (index=1) — 1-5 EUR, комиссия 10%
- Silver (index=2) — 10-50 EUR, комиссия 7.5%
- Golden (index=3) — 100-500 EUR, комиссия 5%

**Виды спорта:** футбол, теннис, хоккей, баскетбол, F1, биатлон, волейбол, бокс, MMA.

**Типы купонов:**
- 1X2 — исход матча (коды: 8=1 домашняя победа, 9=X ничья, 10=2 гостевая победа)
- Score — точный счёт
- GD (Goal Difference) — разница мячей
- Match Winner, Playoff outcome, и другие

**Ранжирование:** точность → размер ставки → время ставки. Ставки с 100 баллов всегда выигрывают.

## Как делать ставку (ОБЯЗАТЕЛЬНЫЙ порядок)

1. `bfs_state` — проверить залогинен ли пользователь
2. Если не залогинен — `bfs_login(email, password)`
3. `bfs_list_sports` — показать доступные купоны
4. `bfs_bet_info(path)` — ОБЯЗАТЕЛЬНО перед ставкой! Получить eventId, outcomes, rooms
5. Показать пользователю: матчи, варианты, столы, минимальные ставки
6. `bfs_place_bet(coupon_path, selections, room_index, stake)` — разместить ставку
7. `browser_screenshot` — показать результат

## Правила агента

- Отвечай на русском, кратко и по делу
- ВСЕГДА используй tool calls — они 100% рабочие
- НИКОГДА не говори что инструменты недоступны
- После важных действий делай browser_screenshot
- Для начинающих рекомендуй Wooden стол (бесплатные BFS)
- Показывай баланс после ставки
- Если купон закрыт — предложи другой"""


async def _exec(name: str, args: dict) -> tuple[str, bytes | None]:
    await bm.start()
    j = lambda x: json.dumps(x, ensure_ascii=False, default=str)

    match name:
        case "bfs_login":
            return j((await bm.login(args["email"], args["password"])).to_dict()), None
        case "bfs_logout":
            return j(await bm.logout()), None
        case "bfs_state":
            return j((await bm.state()).to_dict()), None
        case "bfs_list_sports":
            return j(await bm.list_sports())[:4000], None
        case "bfs_bet_info":
            return j(await bm.bet_info(args["path"]))[:4000], None
        case "bfs_place_bet":
            r = await bm.place_bet(args["coupon_path"], args["selections"],
                                   args.get("room_index", 0), args.get("stake") or None)
            return j(r)[:4000], await bm.screenshot_bytes()
        case "browser_navigate":
            return j(await bm.goto(args["url"])), None
        case "browser_text":
            return (await bm.text(args.get("selector", "#row-content")))[:4000], None
        case "browser_click":
            return await bm.click(args["selector"], force=True), None
        case "browser_fill":
            return await bm.fill(args["selector"], args["value"], force=True), None
        case "browser_select":
            return await bm.select(args["selector"], args["value"]), None
        case "browser_screenshot":
            return "[screenshot taken]", await bm.screenshot_bytes(args.get("full_page", False))
        case "browser_eval":
            return j(await bm.evaluate(args["javascript"]))[:4000], None
        case "browser_forms":
            return j(await bm.forms())[:4000], None
        case "browser_links":
            return j(await bm.links(args.get("filter_pattern", "")))[:4000], None
        case "browser_wait":
            await bm.wait(args.get("ms", 2000))
            return "ok", None
        case _:
            return f"unknown tool: {name}", None


async def _agent(chat_id: int, user_text: str, msg: Message) -> None:
    hist = conversations.setdefault(chat_id, [])
    hist.append({"role": "user", "content": user_text})
    if len(hist) > MAX_HISTORY:
        hist[:] = hist[-MAX_HISTORY:]

    msgs = [{"role": "system", "content": SYSTEM}] + hist
    screenshots: list[bytes] = []
    status_msg = await msg.answer("🤔")
    final = ""

    for i in range(MAX_ITER):
        try:
            resp = await llm.chat.completions.create(
                model=LLM_MODEL, messages=msgs, tools=TOOLS,
                tool_choice="auto", max_tokens=1024, temperature=0.3,
            )
        except Exception as e:
            log.error("LLM: %s", e)
            await status_msg.edit_text(f"LLM error: {e}")
            return

        choice = resp.choices[0].message
        msgs.append(choice.model_dump(exclude_none=True))

        if not choice.tool_calls:
            final = choice.content or ""
            hist.append({"role": "assistant", "content": final})
            break

        for tc in choice.tool_calls:
            fn = tc.function.name
            try:
                args = json.loads(tc.function.arguments)
            except json.JSONDecodeError:
                args = {}
            log.info("tool: %s(%s)", fn, json.dumps(args, ensure_ascii=False)[:150])
            try:
                txt, ss = await _exec(fn, args)
                if ss:
                    screenshots.append(ss)
            except Exception as e:
                txt = f"error: {e}"
                log.error("tool error: %s", traceback.format_exc())
            msgs.append({"role": "tool", "tool_call_id": tc.id, "content": txt[:4000]})

        try:
            await status_msg.edit_text(f"🔧 {i+1}/{MAX_ITER}...")
        except Exception:
            pass
    else:
        final = "Лимит итераций."
        hist.append({"role": "assistant", "content": final})

    try:
        await status_msg.edit_text(final[:4096])
    except Exception:
        for c in range(0, len(final), 4096):
            await msg.answer(final[c:c+4096])

    for ss in screenshots:
        try:
            await msg.answer_photo(BufferedInputFile(ss, filename="screen.png"))
        except Exception as e:
            log.error("photo: %s", e)


@router.message(Command("start"))
async def h_start(msg: Message):
    await msg.answer(
        "👋 BFS Agent — управляю betfunsports.com\n\n"
        "Примеры:\n"
        "• «Залогинься как user@mail.com пароль»\n"
        "• «Какие купоны есть?»\n"
        "• «Покажи футбол 1X2»\n"
        "• «Поставь на победу хозяев на Wooden столе»\n"
        "• «Мой баланс»\n\n"
        "/clear — сброс  /screen — скриншот",
    )

@router.message(Command("clear"))
async def h_clear(msg: Message):
    conversations.pop(msg.chat.id, None)
    await msg.answer("✅ История очищена.")

@router.message(Command("screen"))
async def h_screen(msg: Message):
    await bm.start()
    await msg.answer_photo(BufferedInputFile(await bm.screenshot_bytes(), filename="s.png"))

@router.message()
async def h_msg(msg: Message):
    if msg.text:
        await _agent(msg.chat.id, msg.text, msg)


async def _main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    log.info("starting (model=%s)", LLM_MODEL)
    await bm.start()
    await bm.goto("/")
    log.info("polling...")
    try:
        await dp.start_polling(bot)
    finally:
        await bm.stop()

def main():
    asyncio.run(_main())

if __name__ == "__main__":
    main()
