#!/usr/bin/env python3
"""
BFS Telegram Bot + LLM — natural language browser agent.
User writes in Telegram → LLM decides which browser tools to call →
executes on headless Chrome → returns result + screenshot.

LLM: DeepSeek Chat via OpenRouter ($0.30/1M input tokens)
Browser: Playwright headless Chromium
"""

import asyncio
import base64
import json
import logging
import sys
import traceback
from typing import Any

sys.path.insert(0, "/workspace/bfs-mcp/src")

from aiogram import Bot, Dispatcher, Router
from aiogram.types import Message, BufferedInputFile
from aiogram.filters import Command
from aiogram.enums import ParseMode
from openai import AsyncOpenAI

from bfs_mcp.browser import BrowserManager

# ── config ────────────────────────────────────────────────────────────

TG_TOKEN = "8491424456:AAG0Rlgk6JoQrdefcSjRPX_jppRWns8naOY"
OR_KEY = "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"
MODEL = "deepseek/deepseek-chat"

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("bfs-bot")

bot = Bot(token=TG_TOKEN)
dp = Dispatcher()
router = Router()
dp.include_router(router)

bm = BrowserManager()

llm = AsyncOpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OR_KEY,
)

conversations: dict[int, list[dict]] = {}
MAX_HISTORY = 30

# ── tool definitions (OpenAI function calling format) ─────────────────

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "browser_navigate",
            "description": "Navigate to a URL. Use absolute URLs or relative paths like /football/prizecoupons1X2. Returns status, URL, title.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "URL or path to navigate to"}
                },
                "required": ["url"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "browser_get_text",
            "description": "Get visible text from current page. Use selector '#row-content' for main content, 'body' for everything.",
            "parameters": {
                "type": "object",
                "properties": {
                    "selector": {"type": "string", "description": "CSS selector", "default": "#row-content"}
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "browser_click",
            "description": "Click an element by CSS selector.",
            "parameters": {
                "type": "object",
                "properties": {
                    "selector": {"type": "string"}
                },
                "required": ["selector"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "browser_fill",
            "description": "Fill a form input field.",
            "parameters": {
                "type": "object",
                "properties": {
                    "selector": {"type": "string", "description": "CSS selector of the input"},
                    "value": {"type": "string", "description": "Value to fill"},
                },
                "required": ["selector", "value"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "browser_select",
            "description": "Select an option in a dropdown.",
            "parameters": {
                "type": "object",
                "properties": {
                    "selector": {"type": "string"},
                    "value": {"type": "string"},
                },
                "required": ["selector", "value"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "browser_screenshot",
            "description": "Take a screenshot of current page. Call this when user wants to see the page or after important actions.",
            "parameters": {
                "type": "object",
                "properties": {
                    "full_page": {"type": "boolean", "default": False}
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "browser_eval",
            "description": "Execute JavaScript in the page. Use for complex DOM queries, data extraction, or form manipulation.",
            "parameters": {
                "type": "object",
                "properties": {
                    "javascript": {"type": "string"}
                },
                "required": ["javascript"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "browser_forms",
            "description": "List all forms on the current page with their fields, types, and visibility.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "browser_links",
            "description": "List links on current page with optional filter.",
            "parameters": {
                "type": "object",
                "properties": {
                    "filter_pattern": {"type": "string", "default": ""}
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "bfs_login",
            "description": "Login to betfunsports.com. The site has anti-bot honeypot fields; this handles them.",
            "parameters": {
                "type": "object",
                "properties": {
                    "email": {"type": "string"},
                    "password": {"type": "string"},
                },
                "required": ["email", "password"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "bfs_logout",
            "description": "Logout from betfunsports.com.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "bfs_state",
            "description": "Get current state: URL, title, auth status, username, EUR/BFS balance.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "bfs_list_sports",
            "description": "List all available sports and coupons from the homepage.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "bfs_view_coupon",
            "description": "View coupon page details: tables, forms, match info.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "e.g. /football/prizecoupons1X2"}
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "browser_wait",
            "description": "Wait N milliseconds. Useful after clicks or navigation for dynamic content.",
            "parameters": {
                "type": "object",
                "properties": {
                    "ms": {"type": "integer", "default": 2000}
                },
            },
        },
    },
]

SYSTEM_PROMPT = """Ты — AI-агент, управляющий сайтом betfunsports.com через headless браузер.
У тебя есть набор инструментов для навигации, кликов, заполнения форм, скриншотов и т.д.

Сайт betfunsports.com — спортивный прогнозный клуб (P2P ставки на спорт).
Виды спорта: футбол, теннис, хоккей, баскетбол, биатлон, F1, волейбол, бокс, MMA.

Правила:
- Отвечай на русском
- Будь кратким и полезным
- После важных действий (навигация, клик, логин) делай скриншот
- Если пользователь просит что-то посмотреть — сначала навигируй, потом извлеки текст и/или сделай скриншот
- Для логина используй bfs_login (он обходит honeypot-защиту)
- Если нужно заполнить форму — сначала вызови browser_forms чтобы увидеть поля
- Можешь вызывать несколько инструментов последовательно
- Страница регистрации: /fullRegistration
- Формат даты рождения: DD/MM/YYYY
- В форме регистрации видимые поля: oldUame (username), oail (email), password0 (пароль), password2 (подтверждение), firstName, lastName, fbirthDate, phone, countryCode (select), sex (radio)
- Скрытые honeypot поля (username, email, password) заполняются автоматически JS перед сабмитом"""


# ── tool execution ────────────────────────────────────────────────────

async def execute_tool(name: str, args: dict) -> tuple[str, bytes | None]:
    """Execute a tool, return (text_result, optional_screenshot_bytes)."""
    await bm.start()
    screenshot_bytes = None

    if name == "browser_navigate":
        r = await bm.goto(args["url"])
        return json.dumps(r, ensure_ascii=False), None

    elif name == "browser_get_text":
        sel = args.get("selector", "#row-content")
        text = await bm.get_text(sel)
        return text[:4000], None

    elif name == "browser_click":
        r = await bm.click(args["selector"], force=True)
        return r, None

    elif name == "browser_fill":
        r = await bm.fill(args["selector"], args["value"], force=True)
        return r, None

    elif name == "browser_select":
        r = await bm.select(args["selector"], args["value"])
        return r, None

    elif name == "browser_screenshot":
        full = args.get("full_page", False)
        b64 = await bm.screenshot(full_page=full)
        screenshot_bytes = base64.b64decode(b64)
        return "[screenshot taken]", screenshot_bytes

    elif name == "browser_eval":
        r = await bm.evaluate(args["javascript"])
        return json.dumps(r, ensure_ascii=False, default=str)[:4000], None

    elif name == "browser_forms":
        r = await bm.evaluate("""() => {
            return Array.from(document.forms).map(f => ({
                id: f.id || '(unnamed)',
                action: f.action,
                method: f.method,
                fields: Array.from(f.elements).filter(e => e.name).map(e => ({
                    name: e.name, type: e.type,
                    value: (e.value||'').substring(0,50),
                    visible: e.offsetParent !== null,
                    options: e.tagName==='SELECT' ? Array.from(e.options).slice(0,5).map(o=>o.value) : undefined
                }))
            })).filter(f => f.fields.length > 0);
        }""")
        return json.dumps(r, ensure_ascii=False)[:4000], None

    elif name == "browser_links":
        pattern = args.get("filter_pattern", "")
        r = await bm.evaluate(f"""() => {{
            const p = "{pattern}";
            return Array.from(document.querySelectorAll('a[href]'))
                .map(a => ({{href: a.getAttribute('href'), text: a.textContent.trim().replace(/\\s+/g,' ').substring(0,60)}}))
                .filter(l => l.href && !l.href.startsWith('/static') && (!p || l.href.includes(p)))
                .filter((v,i,a) => a.findIndex(x => x.href===v.href)===i).slice(0,30);
        }}""")
        return json.dumps(r, ensure_ascii=False)[:4000], None

    elif name == "bfs_login":
        state = await bm.login(args["email"], args["password"])
        r = {
            "authenticated": state.is_authenticated,
            "username": state.username,
            "balance_eur": state.balance_eur,
            "balance_bfs": state.balance_bfs,
        }
        return json.dumps(r, ensure_ascii=False), None

    elif name == "bfs_logout":
        r = await bm.logout()
        return json.dumps(r, ensure_ascii=False), None

    elif name == "bfs_state":
        s = await bm.get_state()
        r = {
            "url": s.url, "title": s.title,
            "authenticated": s.is_authenticated,
            "username": s.username,
            "balance_eur": s.balance_eur,
            "balance_bfs": s.balance_bfs,
            "in_game": s.in_game,
        }
        return json.dumps(r, ensure_ascii=False), None

    elif name == "bfs_list_sports":
        sports = await bm.list_sports()
        return json.dumps(sports, ensure_ascii=False)[:4000], None

    elif name == "bfs_view_coupon":
        details = await bm.get_coupon_details(args["path"])
        return json.dumps(details, ensure_ascii=False)[:4000], None

    elif name == "browser_wait":
        ms = args.get("ms", 2000)
        await bm.wait(ms)
        return f"Waited {ms}ms", None

    return f"Unknown tool: {name}", None


# ── LLM agent loop ───────────────────────────────────────────────────

async def agent_respond(chat_id: int, user_text: str, msg: Message) -> None:
    """Full agent loop: user msg → LLM → tool calls → LLM → response."""
    if chat_id not in conversations:
        conversations[chat_id] = []

    history = conversations[chat_id]
    history.append({"role": "user", "content": user_text})

    if len(history) > MAX_HISTORY:
        history[:] = history[-MAX_HISTORY:]

    messages = [{"role": "system", "content": SYSTEM_PROMPT}] + history

    pending_screenshots: list[bytes] = []
    max_iterations = 8

    thinking_msg = await msg.answer("🤔 Думаю...")

    for iteration in range(max_iterations):
        try:
            response = await llm.chat.completions.create(
                model=MODEL,
                messages=messages,
                tools=TOOLS,
                tool_choice="auto",
                max_tokens=1024,
                temperature=0.3,
            )
        except Exception as e:
            log.error("LLM error: %s", e)
            await thinking_msg.edit_text(f"Ошибка LLM: {e}")
            return

        choice = response.choices[0]
        assistant_msg = choice.message

        messages.append(assistant_msg.model_dump(exclude_none=True))

        if not assistant_msg.tool_calls:
            final_text = assistant_msg.content or "(нет ответа)"
            history.append({"role": "assistant", "content": final_text})
            break

        for tc in assistant_msg.tool_calls:
            fn_name = tc.function.name
            try:
                fn_args = json.loads(tc.function.arguments)
            except json.JSONDecodeError:
                fn_args = {}

            log.info("Tool call: %s(%s)", fn_name, json.dumps(fn_args, ensure_ascii=False)[:200])

            try:
                result_text, screenshot = await execute_tool(fn_name, fn_args)
                if screenshot:
                    pending_screenshots.append(screenshot)
            except Exception as e:
                result_text = f"Error: {e}"
                log.error("Tool error: %s", traceback.format_exc())

            messages.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": result_text[:4000],
            })

        await thinking_msg.edit_text(f"🔧 Выполняю ({iteration + 1}/{max_iterations})...")
    else:
        final_text = "Достигнут лимит итераций. Вот что удалось сделать."
        history.append({"role": "assistant", "content": final_text})

    try:
        await thinking_msg.edit_text(final_text[:4096])
    except Exception:
        for chunk_start in range(0, len(final_text), 4096):
            await msg.answer(final_text[chunk_start : chunk_start + 4096])

    for ss in pending_screenshots:
        try:
            photo = BufferedInputFile(ss, filename="screenshot.png")
            await msg.answer_photo(photo)
        except Exception as e:
            log.error("Screenshot send error: %s", e)


# ── handlers ──────────────────────────────────────────────────────────

@router.message(Command("start"))
async def cmd_start(msg: Message):
    await msg.answer(
        "👋 Я — AI-агент для betfunsports.com\n\n"
        "Пиши на естественном языке, я управляю сайтом через headless браузер.\n\n"
        "Примеры:\n"
        "• «Покажи главную страницу»\n"
        "• «Залогинься как user@mail.com пароль123»\n"
        "• «Какие виды спорта есть?»\n"
        "• «Открой футбольные купоны»\n"
        "• «Покажи баланс»\n"
        "• «Сделай скриншот»\n\n"
        "/clear — очистить историю диалога\n"
        "/screen — быстрый скриншот",
    )


@router.message(Command("clear"))
async def cmd_clear(msg: Message):
    conversations.pop(msg.chat.id, None)
    await msg.answer("История очищена.")


@router.message(Command("screen"))
async def cmd_screen(msg: Message):
    await bm.start()
    b64 = await bm.screenshot()
    photo = BufferedInputFile(base64.b64decode(b64), filename="screen.png")
    await msg.answer_photo(photo)


@router.message()
async def handle_message(msg: Message):
    if not msg.text:
        return
    await agent_respond(msg.chat.id, msg.text, msg)


# ── main ──────────────────────────────────────────────────────────────

async def main():
    log.info("Starting BFS AI Bot (model=%s)...", MODEL)
    await bm.start()
    await bm.goto("/")
    log.info("Browser ready, polling...")
    try:
        await dp.start_polling(bot)
    finally:
        await bm.stop()


if __name__ == "__main__":
    asyncio.run(main())
