"""Optional Telegram notifier placeholder for future extension."""

from __future__ import annotations

import requests

from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID


def send_telegram_message(text: str) -> bool:
    """Send a Telegram message when token and chat id are configured."""

    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("[Telegram] Missing configuration. Skip Telegram sending.")
        return False

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    try:
        response = requests.post(
            url,
            json={"chat_id": TELEGRAM_CHAT_ID, "text": text, "disable_web_page_preview": False},
            timeout=20,
        )
        response.raise_for_status()
        print("[Telegram] Message sent successfully.")
        return True
    except requests.RequestException as exc:
        print(f"[Telegram] Failed to send message: {exc}")
        return False
