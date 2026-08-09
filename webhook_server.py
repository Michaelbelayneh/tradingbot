"""
Receives trading signals via HTTP POST and executes them on MT5.

Expected JSON body:
{
    "symbol": "EURUSD",
    "side": "buy",          // or "sell"
    "volume": 0.01,          // optional, defaults to DEFAULT_VOLUME
    "sl": 1.0820,            // optional, absolute price
    "tp": 1.0900,            // optional, absolute price
    "signal_id": "abc123"    // optional, for your own tracking
}

Auth: header  X-Webhook-Secret: <WEBHOOK_SECRET from .env>

Example curl:
curl -X POST http://localhost:5000/webhook \
  -H "Content-Type: application/json" \
  -H "X-Webhook-Secret: your_secret" \
  -d '{"symbol":"EURUSD","side":"buy","sl":1.0820,"tp":1.0900}'

For GitHub Actions / TradingView / any external source to reach this,
the machine running this script needs to be reachable from the internet
(port-forward your router, or use a tunnel like ngrok/Cloudflare Tunnel).
"""
import logging
from flask import Flask, request, jsonify

import config
import mt5_client
import telegram_bot

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(message)s")
log = logging.getLogger("webhook")

app = Flask(__name__)


@app.before_request
def check_secret():
    if request.path != "/webhook":
        return
    secret = request.headers.get("X-Webhook-Secret")
    if secret != config.WEBHOOK_SECRET:
        log.warning("Rejected request with bad/missing secret from %s", request.remote_addr)
        return jsonify({"error": "unauthorized"}), 401


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})


@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "invalid or missing JSON body"}), 400

    symbol = data.get("symbol")
    side = data.get("side")
    if not symbol or not side:
        return jsonify({"error": "symbol and side are required"}), 400

    volume = data.get("volume")
    sl = data.get("sl")
    tp = data.get("tp")
    signal_id = data.get("signal_id")

    log.info("Signal received: %s %s vol=%s sl=%s tp=%s id=%s",
              symbol, side, volume, sl, tp, signal_id)

    result = mt5_client.place_order(
        symbol=symbol, side=side, volume=volume, sl=sl, tp=tp,
        comment=f"sig:{signal_id}" if signal_id else "webhook"
    )

    if result is None:
        telegram_bot.notify_error(f"Failed to place {side} {symbol}: no result from MT5 (see logs)")
        return jsonify({"error": "order failed, see server logs"}), 500

    import MetaTrader5 as mt5
    if result.retcode != mt5.TRADE_RETCODE_DONE:
        telegram_bot.notify_error(f"Order rejected: {symbol} {side} — {result.comment}")
        return jsonify({"error": result.comment, "retcode": result.retcode}), 400

    telegram_bot.notify_trade_opened(
        symbol=symbol, side=side, volume=volume or config.DEFAULT_VOLUME,
        entry_price=result.price, sl=sl, tp=tp, ticket=result.order,
        signal_id=signal_id,
    )

    return jsonify({
        "status": "executed",
        "ticket": result.order,
        "price": result.price,
    })


def run():
    if not mt5_client.connect():
        raise SystemExit("Could not connect to MT5 — check credentials/server/terminal path in .env")
    telegram_bot.notify_info("Webhook server started and connected to MT5.")
    app.run(host=config.WEBHOOK_HOST, port=config.WEBHOOK_PORT)


if __name__ == "__main__":
    run()
