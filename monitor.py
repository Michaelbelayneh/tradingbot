"""
Polls MT5 trade history every few seconds. When a position that this
bot opened (matched by MAGIC_NUMBER) disappears from open positions,
it looks up the closing deal and reports profit to Telegram.
"""
import time
import logging
from datetime import datetime, timedelta

import config
import mt5_client
import telegram_bot

log = logging.getLogger("monitor")

POLL_SECONDS = 5


def run(stop_event=None):
    known_tickets = {p.ticket: p for p in mt5_client.get_open_positions()}
    log.info("Monitor started. Tracking %d open position(s).", len(known_tickets))

    while True:
        if stop_event is not None and stop_event.is_set():
            break
        try:
            current = {p.ticket: p for p in mt5_client.get_open_positions()}
            closed_tickets = set(known_tickets) - set(current)

            for ticket in closed_tickets:
                pos = known_tickets[ticket]
                _report_close(ticket, pos)

            known_tickets = current
        except Exception as e:
            log.error("Monitor loop error: %s", e)

        time.sleep(POLL_SECONDS)


def _report_close(ticket, pos):
    now = datetime.now()
    deals = mt5_client.get_recent_deals(now - timedelta(hours=6), now + timedelta(minutes=1))
    close_deals = [d for d in deals if d.position_id == ticket]

    if not close_deals:
        telegram_bot.notify_info(f"Position #{ticket} on {pos.symbol} closed (details unavailable).")
        return

    total_profit = sum(d.profit + d.swap + d.commission for d in close_deals)
    last_deal = close_deals[-1]
    side = "buy" if pos.type == 0 else "sell"

    telegram_bot.notify_trade_closed(
        symbol=pos.symbol,
        side=side,
        volume=pos.volume,
        entry_price=pos.price_open,
        close_price=last_deal.price,
        profit=total_profit,
        ticket=ticket,
    )
    log.info("Reported close for #%s: profit=%.2f", ticket, total_profit)
