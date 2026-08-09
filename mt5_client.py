"""
Wraps the MetaTrader5 package: connect, place orders with SL/TP,
and read open/closed positions. Only runs on Windows with the
MT5 terminal installed and this account added to it.
"""
import logging
import MetaTrader5 as mt5
import config

log = logging.getLogger("mt5")


def connect() -> bool:
    kwargs = {}
    if config.MT5_TERMINAL_PATH:
        kwargs["path"] = config.MT5_TERMINAL_PATH

    if not mt5.initialize(**kwargs):
        log.error("MT5 initialize() failed: %s", mt5.last_error())
        return False

    authorized = mt5.login(
        config.MT5_LOGIN,
        password=config.MT5_PASSWORD,
        server=config.MT5_SERVER,
    )
    if not authorized:
        log.error("MT5 login failed: %s", mt5.last_error())
        mt5.shutdown()
        return False

    info = mt5.account_info()
    log.info("Connected to MT5. Account: %s | Balance: %s | Server: %s",
              info.login, info.balance, info.server)
    return True


def shutdown():
    mt5.shutdown()


def _symbol_ready(symbol: str) -> bool:
    info = mt5.symbol_info(symbol)
    if info is None:
        log.error("Symbol %s not found", symbol)
        return False
    if not info.visible:
        if not mt5.symbol_select(symbol, True):
            log.error("Could not select symbol %s", symbol)
            return False
    return True


def open_positions_count() -> int:
    positions = mt5.positions_get(group="*") or []
    return len([p for p in positions if p.magic == config.MAGIC_NUMBER])


def place_order(symbol: str, side: str, volume: float = None, sl: float = None,
                 tp: float = None, comment: str = "signal"):
    """
    side: 'buy' or 'sell'
    sl / tp: absolute price levels (float). Pass None to skip.
    Returns the MT5 order_send result, or None on failure.
    """
    side = side.lower()
    if side not in ("buy", "sell"):
        raise ValueError("side must be 'buy' or 'sell'")

    if not _symbol_ready(symbol):
        return None

    if open_positions_count() >= config.MAX_OPEN_TRADES:
        log.warning("Max open trades reached (%s). Skipping signal.", config.MAX_OPEN_TRADES)
        return None

    volume = volume or config.DEFAULT_VOLUME
    tick = mt5.symbol_info_tick(symbol)
    price = tick.ask if side == "buy" else tick.bid
    order_type = mt5.ORDER_TYPE_BUY if side == "buy" else mt5.ORDER_TYPE_SELL

    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol,
        "volume": float(volume),
        "type": order_type,
        "price": price,
        "deviation": 20,
        "magic": config.MAGIC_NUMBER,
        "comment": comment,
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }
    if sl:
        request["sl"] = float(sl)
    if tp:
        request["tp"] = float(tp)

    result = mt5.order_send(request)
    if result is None:
        log.error("order_send returned None: %s", mt5.last_error())
        return None
    if result.retcode != mt5.TRADE_RETCODE_DONE:
        log.error("Order failed, retcode=%s comment=%s", result.retcode, result.comment)
        return result

    log.info("Order placed: %s %s %s lots @ %s (ticket %s)",
              side, symbol, volume, price, result.order)
    return result


def close_position(ticket: int):
    positions = mt5.positions_get(ticket=ticket)
    if not positions:
        log.error("Position %s not found for closing", ticket)
        return None
    pos = positions[0]
    tick = mt5.symbol_info_tick(pos.symbol)
    is_buy = pos.type == mt5.ORDER_TYPE_BUY
    close_price = tick.bid if is_buy else tick.ask
    order_type = mt5.ORDER_TYPE_SELL if is_buy else mt5.ORDER_TYPE_BUY

    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": pos.symbol,
        "volume": pos.volume,
        "type": order_type,
        "position": ticket,
        "price": close_price,
        "deviation": 20,
        "magic": config.MAGIC_NUMBER,
        "comment": "manual close",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }
    return mt5.order_send(request)


def get_open_positions():
    positions = mt5.positions_get() or []
    return [p for p in positions if p.magic == config.MAGIC_NUMBER]


def get_recent_deals(from_ts, to_ts):
    """Deals (fills) in a time range — used to detect closes and their profit."""
    deals = mt5.history_deals_get(from_ts, to_ts)
    return list(deals) if deals else []
