"""
Simple Telegram sender. Get TELEGRAM_BOT_TOKEN from @BotFather,
and TELEGRAM_CHAT_ID by messaging your bot then visiting:
https://api.telegram.org/bot<TOKEN>/getUpdates
"""
import requests
import logging
import config

log = logging.getLogger("telegram")

API_URL = f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}/sendMessage"


def send(text: str) -> None:
    try:
        resp = requests.post(
            API_URL,
            json={
                "chat_id": config.TELEGRAM_CHAT_ID,
                "text": text,
                "parse_mode": "HTML",
            },
            timeout=10,
        )
        if not resp.ok:
            log.error("Telegram send failed: %s", resp.text)
    except Exception as e:
        log.error("Telegram send exception: %s", e)


def notify_trade_opened(symbol, side, volume, entry_price, sl, tp, ticket, signal_id=None):
    text = (
        f"🟢 <b>TRADE OPENED</b>\n"
        f"Symbol: <b>{symbol}</b>\n"
        f"Side: <b>{side.upper()}</b>\n"
        f"Volume: {volume}\n"
        f"Entry: {entry_price}\n"
        f"SL: {sl if sl else '-'}\n"
        f"TP: {tp if tp else '-'}\n"
        f"Ticket: #{ticket}\n"
        + (f"Signal ID: {signal_id}\n" if signal_id else "")
    )
    send(text)


def notify_trade_closed(symbol, side, volume, entry_price, close_price, profit, ticket, reason="closed"):
    emoji = "✅" if profit >= 0 else "❌"
    text = (
        f"{emoji} <b>TRADE CLOSED</b> ({reason})\n"
        f"Symbol: <b>{symbol}</b>\n"
        f"Side: <b>{side.upper()}</b>\n"
        f"Volume: {volume}\n"
        f"Entry: {entry_price}\n"
        f"Close: {close_price}\n"
        f"Profit: <b>{profit:.2f}</b>\n"
        f"Ticket: #{ticket}"
    )
    send(text)


def notify_error(msg: str):
    send(f"⚠️ <b>ERROR</b>\n{msg}")


def notify_info(msg: str):
    send(f"ℹ️ {msg}")
