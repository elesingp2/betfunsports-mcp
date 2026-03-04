"""BFS Telegram Bot — LLM agent that drives betfunsports.com via headless browser."""

from __future__ import annotations

import asyncio
import base64
import json
import logging
import os
import traceback
from typing import Any

from aiogram import Bot, Dispatcher, Router
from aiogram.types import Message, BufferedInputFile
from aiogram.filters import Command
from aiogram.enums import ParseMode
from openai import AsyncOpenAI

from .browser import BFSBrowser

log = logging.getLogger(__name__)

# ── config (env) ──────────────────────────────────────────────────────

TG_TOKEN = os.environ["BFS_TG_TOKEN"]
LLM_KEY = os.environ["BFS_LLM_KEY"]
LLM_BASE = os.environ.get("BFS_LLM_BASE", "https://openrouter.ai/api/v1")
LLM_MODEL = os.environ.get("BFS_LLM_MODEL", "deepseek/deepseek-chat")
MAX_HISTORY = int(os.environ.get("BFS_MAX_HISTORY", "30"))
MAX_ITER = int(os.environ.get("BFS_MAX_ITER", "8"))

# ── singletons ────────────────────────────────────────────────────────

bot = Bot(token=TG_TOKEN)
dp = Dispatcher()
router = Router()
dp.include_router(router)

bm = BFSBrowser()
llm = AsyncOpenAI(base_url=LLM_BASE, api_key=LLM_KEY)
conversations: dict[int, list[dict]] = {}

# ── tool defs (OpenAI function-calling) ───────────────────────────────

TOOLS: list[dict] = [
    _t("bfs_login", "Login to betfunsports.com.", {"email": "string", "password": "string"}, ["email", "password"])
    if False else None,  # built below
]

def _td(name: str, desc: str, props: dict[str, Any], req: list[str] | None = None) -> dict:
    schema: dict = {"type": "object", "properties": {}}
    for k, v in props.items():
        if isinstance(v, str):
            schema["properties"][k] = {"type": v}
        else:
            schema["properties"][k] = v
    if req:
        schema["required"] = req
    return {"type": "function", "function": {"name": name, "description": desc, "parameters": schema}}


TOOLS = [
    _td("bfs_login", "Login to betfunsports.com.", {"email": "string", "password": "string"}, ["email", "password"]),
    _td("bfs_logout", "Logout.", {}),
    _td("bfs_state", "Current state: URL, auth, balance.", {}),
    _td("bfs_list_sports", "List all sports / coupons.", {}),
    _td("bfs_bet_info", "Parse coupon page into events, outcomes, rooms. Call before placing bet.",
        {"path": "string"}, ["path"]),
    _td("bfs_place_bet",
        "Place a bet. selections: {eventId: outcomeCode}. 1X2 codes: 8=home,9=draw,10=away. "
        "room_index: 0=Wooden(TOT) 1=Bronze(EUR) 2=Silver 3=Golden.",
        {"coupon_path": "string",
         "selections": {"type": "object", "description": "{eventId: outcomeCode}", "additionalProperties": {"type": "string"}},
         "room_index": {"type": "integer", "default": 0},
         "stake": {"type": "string", "default": ""}},
        ["coupon_path", "selections"]),
    _td("browser_navigate", "Navigate to URL or path.", {"url": "string"}, ["url"]),
    _td("browser_text", "Get page text.", {"selector": {"type": "string", "default": "#row-content"}}),
    _td("browser_click", "Click element.", {"selector": "string"}, ["selector"]),
    _td("browser_fill", "Fill input.", {"selector": "string", "value": "string"}, ["selector", "value"]),
    _td("browser_select", "Select dropdown.", {"selector": "string", "value": "string"}, ["selector", "value"]),
    _td("browser_screenshot", "Screenshot (call after important actions).",
        {"full_page": {"type": "boolean", "default": False}}),
    _td("browser_eval", "Execute JS in page.", {"javascript": "string"}, ["javascript"]),
    _td("browser_forms", "List all forms with fields.", {}),
    _td("browser_links", "List page links.", {"filter_pattern": {"type": "string", "default": ""}}),
    _td("browser_wait", "Wait ms.", {"ms": {"type": "integer", "default": 2000}}),
]

SYSTEM = """Ты — AI-агент, управляющий betfunsports.com через headless браузер.
Отвечай на русском, кратко.

## Ставки
- Список купонов: /football/prizecoupons1X2, /football/prizecouponsScore и т.д.
- Купон: /FOOTBALL/prizecoupons1X2/18580
- Перед ставкой ВСЕГДА вызови bfs_bet_info — получишь events, outcomes, rooms
- 1X2 коды: 8=победа хозяев(1), 9=ничья(X), 10=победа гостей(2)
- Комнаты: 0=Wooden(TOT), 1=Bronze(EUR), 2=Silver(EUR), 3=Golden(EUR)
- Для ставки: bfs_place_bet(coupon_path, selections={eventId:outcomeCode}, room_index, stake)

## Правила
- Проверяй bfs_state — залогинен ли пользователь
- Для логина используй bfs_login (обходит honeypot)
- После действий делай browser_screenshot
- Если купон закрыт — сообщи
- Регистрация: /fullRegistration, поля: oldUame, oail, password0, password2, firstName, lastName, fbirthDate (DD/MM/YYYY), phone, countryCode"""


# ── tool execution ────────────────────────────────────────────────────

async def _exec(name: str, args: dict) -> tuple[str, bytes | None]:
    await bm.start()
    ss = None

    if name == "bfs_login":
        return json.dumps((await bm.login(args["email"], args["password"])).to_dict(), ensure_ascii=False), None
    if name == "bfs_logout":
        return json.dumps(await bm.logout(), ensure_ascii=False), None
    if name == "bfs_state":
        return json.dumps((await bm.state()).to_dict(), ensure_ascii=False), None
    if name == "bfs_list_sports":
        return json.dumps(await bm.list_sports(), ensure_ascii=False)[:4000], None
    if name == "bfs_bet_info":
        return json.dumps(await bm.bet_info(args["path"]), ensure_ascii=False)[:4000], None
    if name == "bfs_place_bet":
        r = await bm.place_bet(args["coupon_path"], args["selections"],
                               args.get("room_index", 0), args.get("stake") or None)
        return json.dumps(r, ensure_ascii=False)[:4000], await bm.screenshot_bytes()
    if name == "browser_navigate":
        return json.dumps(await bm.goto(args["url"]), ensure_ascii=False), None
    if name == "browser_text":
        return (await bm.text(args.get("selector", "#row-content")))[:4000], None
    if name == "browser_click":
        return await bm.click(args["selector"], force=True), None
    if name == "browser_fill":
        return await bm.fill(args["selector"], args["value"], force=True), None
    if name == "browser_select":
        return await bm.select(args["selector"], args["value"]), None
    if name == "browser_screenshot":
        return "[screenshot]", await bm.screenshot_bytes(args.get("full_page", False))
    if name == "browser_eval":
        return json.dumps(await bm.evaluate(args["javascript"]), ensure_ascii=False, default=str)[:4000], None
    if name == "browser_forms":
        return json.dumps(await bm.forms(), ensure_ascii=False)[:4000], None
    if name == "browser_links":
        return json.dumps(await bm.links(args.get("filter_pattern", "")), ensure_ascii=False)[:4000], None
    if name == "browser_wait":
        await bm.wait(args.get("ms", 2000))
        return "ok", None

    return f"unknown tool: {name}", None


# ── LLM agent loop ───────────────────────────────────────────────────

async def _agent(chat_id: int, user_text: str, msg: Message) -> None:
    hist = conversations.setdefault(chat_id, [])
    hist.append({"role": "user", "content": user_text})
    if len(hist) > MAX_HISTORY:
        hist[:] = hist[-MAX_HISTORY:]

    msgs = [{"role": "system", "content": SYSTEM}] + hist
    screenshots: list[bytes] = []
    status_msg = await msg.answer("🤔")

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
        for chunk in range(0, len(final), 4096):
            await msg.answer(final[chunk:chunk+4096])

    for ss in screenshots:
        try:
            await msg.answer_photo(BufferedInputFile(ss, filename="screen.png"))
        except Exception as e:
            log.error("photo send: %s", e)


# ── handlers ──────────────────────────────────────────────────────────

@router.message(Command("start"))
async def h_start(msg: Message):
    await msg.answer(
        "👋 BFS Agent — управляю betfunsports.com через браузер.\n\n"
        "Пиши на естественном языке:\n"
        "• «Залогинься как user@mail.com пароль»\n"
        "• «Какие виды спорта?»\n"
        "• «Покажи купоны футбол 1X2»\n"
        "• «Поставь на победу хозяев»\n"
        "• «Баланс»\n"
        "• «Скриншот»\n\n"
        "/clear — сброс диалога  /screen — скриншот",
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


# ── entry point ───────────────────────────────────────────────────────

async def _main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    log.info("starting bot (model=%s)...", LLM_MODEL)
    await bm.start()
    await bm.goto("/")
    log.info("browser ready, polling...")
    try:
        await dp.start_polling(bot)
    finally:
        await bm.stop()


def main():
    asyncio.run(_main())


if __name__ == "__main__":
    main()
