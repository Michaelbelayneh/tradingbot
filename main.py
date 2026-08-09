"""
Run this file. It starts:
  1) the Flask webhook server (receives signals, opens trades)
  2) a background thread that watches for closed trades and
     reports profit/loss to Telegram

Usage:
    python main.py
"""
import logging
import threading

import config
import mt5_client
import telegram_bot
import monitor
import webhook_server

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(message)s")
log = logging.getLogger("main")


def main():
    if not mt5_client.connect():
        raise SystemExit("Could not connect to MT5 — check .env (login/password/server) "
                          "and that the MT5 terminal is installed at MT5_TERMINAL_PATH.")

    telegram_bot.notify_info(
        f"Bot online. Watching account {config.MT5_LOGIN} on {config.MT5_SERVER}."
    )

    stop_event = threading.Event()
    monitor_thread = threading.Thread(target=monitor.run, args=(stop_event,), daemon=True)
    monitor_thread.start()
    log.info("Close-monitor thread started.")

    try:
        webhook_server.app.run(host=config.WEBHOOK_HOST, port=config.WEBHOOK_PORT)
    finally:
        stop_event.set()
        mt5_client.shutdown()


if __name__ == "__main__":
    main()
