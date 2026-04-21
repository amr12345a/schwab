from schwab.orders.equities import equity_buy_market, equity_sell_market

from .config import get_settings
from .models import TradingViewSignal, TradeResult
from .schwab_client import get_client


def _build_order(signal: TradingViewSignal, quantity: int):
    if signal.action == "BUY":
        return equity_buy_market(signal.symbol, quantity).build()
    if signal.action == "SELL":
        return equity_sell_market(signal.symbol, quantity).build()
    raise ValueError(f"Unsupported action: {signal.action}")


def execute_signal(signal: TradingViewSignal, account_hash: str | None = None) -> TradeResult:
    settings = get_settings()
    quantity = signal.quantity or settings.default_order_qty
    client = get_client()
    resolved_account_hash = account_hash or settings.schwab_account_hash

    if not resolved_account_hash:
        raise RuntimeError("No active Schwab account selected. Choose one at /trader/v1/accounts first.")

    if settings.dry_run:
        return TradeResult(
            ok=True,
            dry_run=True,
            action=signal.action,
            symbol=signal.symbol,
            quantity=quantity,
            account_hash=resolved_account_hash,
            order_id=None,
            message="Dry run enabled, order not submitted",
        )

    order_spec = _build_order(signal, quantity)
    response = client.place_order(resolved_account_hash, order_spec)

    order_id = None
    if hasattr(response, "headers"):
        order_id = response.headers.get("location")

    return TradeResult(
        ok=True,
        dry_run=False,
        action=signal.action,
        symbol=signal.symbol,
        quantity=quantity,
        account_hash=resolved_account_hash,
        order_id=order_id,
        message="Order submitted to Schwab",
    )
