"""Telegram notifications — keeps server.py tool functions clean."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)

_TG_CONFIG = Path.home() / ".bfs-mcp" / "telegram.json"


def _update_tg_config(email: str, balance_eur: str = "", balance_bfs: str = "") -> None:
    try:
        config: dict = {}
        if _TG_CONFIG.exists():
            config = json.loads(_TG_CONFIG.read_text())
        config["logged_in_as"] = email
        config["balance_eur"] = balance_eur
        config["balance_bfs"] = balance_bfs
        _TG_CONFIG.write_text(json.dumps(config, indent=2))
    except Exception:
        log.debug("tg config update failed", exc_info=True)

try:
    from bfs_bot.notify import send_text, send_photo
except ImportError:
    send_text = send_photo = None


def _text(msg: str) -> None:
    if not send_text:
        return
    try:
        send_text(msg)
    except Exception:
        log.debug("telegram notify failed", exc_info=True)


def _photo(data: bytes, caption: str = "") -> None:
    if not send_photo:
        return
    try:
        send_photo(data, caption=caption)
    except Exception:
        log.debug("telegram photo notify failed", exc_info=True)


# ── high-level events ────────────────────────────────────────────────

def on_register(email: str, result: dict[str, Any]) -> None:
    if result.get("success"):
        _text(f"🆕 <b>REGISTER</b>: {email}\n{result.get('message', 'OK')}")
    elif result.get("errors"):
        _text(f"❌ <b>REGISTER FAILED</b>: {email}\n{'; '.join(result['errors'])}")


def on_login(email: str, result: dict[str, Any]) -> None:
    if result.get("authenticated"):
        _update_tg_config(email, result.get("balance_eur", ""), result.get("balance_bfs", ""))
        _text(
            f"✅ <b>LOGIN</b>: {email}\n"
            f"EUR: {result.get('balance_eur', '?')} | "
            f"BFS: {result.get('balance_bfs', '?')} | "
            f"In-game: {result.get('in_game', '?')}"
        )
    elif result.get("error"):
        _text(f"❌ <b>LOGIN FAILED</b>: {email}\n{result['error']}")


def on_bet(result: dict[str, Any], coupon_path: str,
           screenshot: bytes | None = None) -> None:
    if result.get("success"):
        cap = (
            f"🎯 <b>BET</b>: {result.get('room', '?')} | "
            f"Stake: {result.get('stake', '?')}"
        )
        if screenshot:
            _photo(screenshot, caption=cap)
        else:
            _text(cap)
    else:
        _text(
            f"❌ <b>BET FAILED</b>: {result.get('error', 'unknown')}\n"
            f"Coupon: {coupon_path}"
        )
