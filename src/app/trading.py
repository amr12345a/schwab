from schwab.orders.equities import equity_buy_market, equity_sell_market

from .config import get_settings
from .models import TestOrderRequest, TradingViewSignal, TradeResult
from .schwab_client import get_client


def _build_market_order(action: str, symbol: str, quantity: int):
    if action == "BUY":
        return equity_buy_market(symbol, quantity).build()
    if action == "SELL":
        return equity_sell_market(symbol, quantity).build()
    raise ValueError(f"Unsupported action: {action}")


def execute_signal(signal: TradingViewSignal, account_hash: str | None = None) -> TradeResult:
    settings = get_settings()
    quantity = signal.quantity or settings.default_order_qty
    client = get_client()
    resolved_account_hash = account_hash or settings.schwab_account_hash

    if not resolved_account_hash:
        raise RuntimeError("No active Schwab account selected. Choose one at /trader/v1/accounts first.")

    print(f"TRANSACTION: {signal.action} {quantity} {signal.symbol} (Account: {resolved_account_hash})")

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

    order_spec = _build_market_order(signal.action, signal.symbol, quantity)
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


def execute_test_order(request: TestOrderRequest, account_hash: str | None = None) -> TradeResult:
    settings = get_settings()
    resolved_account_hash = account_hash or settings.schwab_account_hash
    if not resolved_account_hash:
        raise RuntimeError("No active Schwab account selected.")

    quantity = request.quantity or settings.default_order_qty
    print(f"TEST ORDER: {request.action} {quantity} {request.symbol} ON {resolved_account_hash}")

    if request.dry_run or settings.dry_run:
        return TradeResult(
            ok=True,
            dry_run=True,
            action=request.action,
            symbol=request.symbol,
            quantity=quantity,
            account_hash=resolved_account_hash,
            order_id=None,
            message="Dry run enabled, order not submitted",
        )

    client = get_client()
    order_spec = _build_market_order(request.action, request.symbol, quantity)
    response = client.place_order(resolved_account_hash, order_spec)

    order_id = None
    if hasattr(response, "headers"):
        order_id = response.headers.get("location")

    return TradeResult(
        ok=True,
        dry_run=False,
        action=request.action,
        symbol=request.symbol,
        quantity=quantity,
        account_hash=resolved_account_hash,
        order_id=order_id,
        message="Test order submitted to Schwab",
    )
