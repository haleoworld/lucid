"""Best-effort Telegram notifications (take done / failed). Never raises.

Uses only the stdlib so it adds no dependency. If TELEGRAM_CHAT_ID isn't set,
it tries to discover your chat id from recent updates — so just message the
bot once from your phone and the next ping will find you.
"""
from __future__ import annotations

import json
import urllib.parse
import urllib.request

from . import config

_API = "https://api.telegram.org/bot{token}/{method}"
_cached_chat_id = ""


def _resolve_chat_id() -> str:
    global _cached_chat_id
    if config.TELEGRAM_CHAT_ID:
        return config.TELEGRAM_CHAT_ID
    if _cached_chat_id:
        return _cached_chat_id
    try:
        url = _API.format(token=config.TELEGRAM_BOT_TOKEN, method="getUpdates")
        with urllib.request.urlopen(url, timeout=5) as r:
            data = json.loads(r.read())
        for upd in reversed(data.get("result", [])):
            msg = upd.get("message") or upd.get("channel_post") or {}
            chat = msg.get("chat") or {}
            if chat.get("id") is not None:
                _cached_chat_id = str(chat["id"])
                return _cached_chat_id
    except Exception:
        pass
    return ""


def send(text: str) -> None:
    if not config.TELEGRAM_BOT_TOKEN:
        return
    chat_id = _resolve_chat_id()
    if not chat_id:
        return
    try:
        url = _API.format(token=config.TELEGRAM_BOT_TOKEN, method="sendMessage")
        payload = urllib.parse.urlencode({
            "chat_id": chat_id, "text": text, "disable_web_page_preview": "true",
        }).encode()
        urllib.request.urlopen(urllib.request.Request(url, data=payload), timeout=5)
    except Exception:
        pass
