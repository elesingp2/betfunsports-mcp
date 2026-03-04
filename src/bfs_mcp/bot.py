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
    _td("bfs_login", "Authenticate with betfunsports.com. Returns username, EUR and BFS balances.",
        {"email": "string", "password": "string"}, ["email", "password"]),
    _td("bfs_logout", "End session."),
    _td("bfs_state", "Check auth status + current balances (EUR, BFS, in-game). ALWAYS call first."),
    _td("bfs_list_sports", "List all available sports coupons. Returns [{path, label}]."),
    _td("bfs_bet_info", "Get coupon details: events, outcomes, rooms, stakes. ALWAYS call before betting.",
        {"path": {"type": "string", "description": "Coupon path, e.g. /FOOTBALL/spainPrimeraDivision/18638"}}, ["path"]),
    _td("bfs_place_bet",
        "Place a bet. selections={eventId: outcomeCode}. 1X2: '8'=home, '9'=draw, '10'=away. "
        "Rooms: 0=Wooden(BFS free) 1=Bronze(1-5€) 2=Silver(10-50€) 3=Golden(100-500€).",
        {"coupon_path": "string",
         "selections": {"type": "object", "additionalProperties": {"type": "string"}},
         "room_index": {"type": "integer", "default": 0},
         "stake": {"type": "string", "default": ""}},
        ["coupon_path", "selections"]),
    _td("bfs_bet_history", "Export bet history as CSV (ID, Coupon, Date, Stake, Points, Winning). Use for analysis."),
    _td("bfs_account", "Get account details: name, email, registration info."),
    _td("bfs_payment_methods", "View deposit/withdrawal methods with fees and limits."),
    _td("page_open", "Open a page by URL or path.",
        {"url": "string"}, ["url"]),
    _td("page_read", "Read text content from current page.",
        {"selector": {"type": "string", "default": "#row-content"}}),
    _td("page_click", "Click an element.", {"selector": "string"}, ["selector"]),
    _td("page_fill", "Fill a form field.", {"selector": "string", "value": "string"}, ["selector", "value"]),
    _td("page_select", "Select dropdown option.", {"selector": "string", "value": "string"}, ["selector", "value"]),
    _td("page_screenshot", "Take a visual snapshot. Call after important actions.",
        {"full_page": {"type": "boolean", "default": False}}),
    _td("page_script", "Run a script for advanced data extraction.",
        {"javascript": "string"}, ["javascript"]),
    _td("page_forms", "List all interactive forms with fields."),
    _td("page_links", "List page links with optional filter.",
        {"filter_pattern": {"type": "string", "default": ""}}),
]

SYSTEM = """Ты — AI-агент платформы Betfunsports. У тебя есть полный набор API-инструментов для работы с платформой.
Ты ОБЯЗАН вызывать tool calls. ВСЕ инструменты рабочие. НИКОГДА не говори что они недоступны.
Отвечай на русском, кратко.

## Betfunsports (TOTUP система)
P2P платформа спортивных прогнозов. Ставки формируют призовой пул, который ПОЛНОСТЬЮ распределяется между победителями.
- 50% ставок выигрывают (ранжирование по точности 0-100 баллов)
- Выигрыш = точность × размер ставки (мин. коэффициент 1.3)
- Ставки с 100 баллов ВСЕГДА выигрывают

## Столы
- Wooden (0) — BFS (бесплатно), 1-10 BFS, 0% комиссии
- Bronze (1) — EUR, 1-5€, 10%
- Silver (2) — EUR, 10-50€, 7.5%
- Golden (3) — EUR, 100-500€, 5%

## Спорт
Футбол, теннис, хоккей, баскетбол, F1, биатлон, волейбол, бокс, MMA.
1X2 коды: "8"=1(дом), "9"=X(ничья), "10"=2(гость)

## Обязательный порядок ставки
1. bfs_state → проверить auth
2. bfs_login → если надо
3. bfs_list_sports → найти купон
4. bfs_bet_info(path) → ОБЯЗАТЕЛЬНО! Получить eventId + rooms
5. bfs_place_bet → разместить
6. page_screenshot → показать результат

## Анализ
- bfs_bet_history → CSV с историей ставок (ID, купон, дата, ставка, баллы, выигрыш)
- Используй для анализа точности и улучшения стратегии

## Правила
- ВСЕГДА используй tool calls
- Новичкам рекомендуй Wooden (бесплатно)
- Для заработка — Silver/Golden (после анализа истории)
- Показывай баланс после ставки
- Закрытый купон → предложи другой"""


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
        case "bfs_bet_history":
            return j(await bm.bet_history())[:4000], None
        case "bfs_account":
            return j(await bm.account_info())[:4000], None
        case "bfs_payment_methods":
            await bm.goto("/paymentmethods")
            return (await bm.text("#row-content"))[:4000], None
        case "page_open":
            return j(await bm.goto(args["url"])), None
        case "page_read":
            return (await bm.text(args.get("selector", "#row-content")))[:4000], None
        case "page_click":
            return await bm.click(args["selector"], force=True), None
        case "page_fill":
            return await bm.fill(args["selector"], args["value"], force=True), None
        case "page_select":
            return await bm.select(args["selector"], args["value"]), None
        case "page_screenshot":
            return "[snapshot taken]", await bm.screenshot_bytes(args.get("full_page", False))
        case "page_script":
            return j(await bm.evaluate(args["javascript"]))[:4000], None
        case "page_forms":
            return j(await bm.forms())[:4000], None
        case "page_links":
            return j(await bm.links(args.get("filter_pattern", "")))[:4000], None
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
