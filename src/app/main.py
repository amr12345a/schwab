from pathlib import Path
import os
import sys
from threading import Lock

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi import FastAPI, HTTPException, Request, status

from app.config import get_settings
from app.models import TestOrderRequest, TradeResult, TradingViewSignal
from app.schwab_client import get_client
from app.trading import execute_signal, execute_test_order

app = FastAPI(title="TradingView to Schwab Bridge", version="0.1.0")
_account_hash_lock = Lock()
_active_account_hash: str | None = None


@app.get("/health")
def health():
    return {"status": "ok"}


def _extract_secret(request: Request, signal: TradingViewSignal) -> str | None:
    query_secret = request.query_params.get("secret")
    if query_secret:
        return query_secret
    return signal.secret


def _initialize_active_account_hash() -> None:
    global _active_account_hash
    get_settings.cache_clear()
    settings = get_settings()
    with _account_hash_lock:
        _active_account_hash = settings.schwab_account_hash or None
    if _active_account_hash:
        print(f"SUCCESS: Trading session active for Schwab account: {_active_account_hash}")
    else:
        print("WARNING: No active Schwab account selected. Webhooks will fail until an account is chosen.")
        print("INFO: You can select an account via GET /trader/v1/accounts?account_hash=<hashValue>")


def _bootstrap_account_hash() -> None:
    existing_hash = os.getenv("SCHWAB_ACCOUNT_HASH")
    if existing_hash:
        print(f"INFO: Using SCHWAB_ACCOUNT_HASH from environment: {existing_hash}")
        return

    paper_account_hash = os.getenv("SCHWAB_PAPER_ACCOUNT_HASH", "").strip()
    real_account_hash = os.getenv("SCHWAB_REAL_ACCOUNT_HASH", "").strip()

    if paper_account_hash and real_account_hash:
        if not sys.stdin.isatty():
            raise RuntimeError(
                "Choose paper or real from an interactive terminal, or set SCHWAB_ACCOUNT_HASH directly before starting the server."
            )

        while True:
            choice = input("Choose Schwab account to use [paper/real]: ").strip().lower()
            if choice in {"paper", "p"}:
                os.environ["SCHWAB_ACCOUNT_HASH"] = paper_account_hash
                print(f"INFO: Paper account hash selected: {paper_account_hash}")
                return
            if choice in {"real", "r"}:
                os.environ["SCHWAB_ACCOUNT_HASH"] = real_account_hash
                print(f"INFO: Real account hash selected: {real_account_hash}")
                return
            print("Please enter paper or real.")

    if paper_account_hash:
        os.environ["SCHWAB_ACCOUNT_HASH"] = paper_account_hash
        print(f"INFO: Only paper account hash found. Using: {paper_account_hash}")
        return

    if real_account_hash:
        os.environ["SCHWAB_ACCOUNT_HASH"] = real_account_hash
        print(f"INFO: Only real account hash found. Using: {real_account_hash}")
        return


def _get_active_account_hash() -> str | None:
    with _account_hash_lock:
        return _active_account_hash


def _set_active_account_hash(account_hash: str, accounts: list[dict]) -> str:
    for account in accounts:
        if str(account.get("hashValue")) == str(account_hash):
            selected_account_hash = str(account_hash)
            global _active_account_hash
            with _account_hash_lock:
                _active_account_hash = selected_account_hash
            os.environ["SCHWAB_ACCOUNT_HASH"] = selected_account_hash
            get_settings.cache_clear()
            return selected_account_hash

    raise RuntimeError(f"Unknown Schwab account hash: {account_hash}")


@app.get("/trader/v1/accounts")
def trader_accounts(account_hash: str | None = None):
    client = get_client()
    response = client.get_account_numbers()

    if response.status_code != status.HTTP_200_OK:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Failed to load Schwab account list")

    accounts = response.json()

    if account_hash is not None:
        try:
            selected_account_hash = _set_active_account_hash(account_hash, accounts)
        except RuntimeError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    else:
        selected_account_hash = _get_active_account_hash()

    return {
        "selected_account_hash": selected_account_hash,
        "accounts": accounts,
        "hint": "Call /trader/v1/accounts?account_hash=<hashValue> to choose the active account.",
    }


@app.post("/webhook/tradingview", response_model=TradeResult)
def tradingview_webhook(signal: TradingViewSignal, request: Request):
    settings = get_settings()
    if settings.tradingview_webhook_secret:
        incoming_secret = _extract_secret(request, signal)
        if incoming_secret != settings.tradingview_webhook_secret:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid webhook secret")

    try:
        return execute_signal(signal, account_hash=_get_active_account_hash())
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc


@app.post("/trader/v1/accounts/test-order", response_model=TradeResult)
def trader_test_order(request_body: TestOrderRequest):
    try:
        return execute_test_order(request_body, account_hash=_get_active_account_hash())
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc


if __name__ == "__main__":
    import uvicorn

    _bootstrap_account_hash()
    _initialize_active_account_hash()
    
    active = _get_active_account_hash()
    if active:
        print(f"READY: Server starting. All orders will target: {active}")
    else:
        print("READY: No account selected. Webhooks will fail until /trader/v1/accounts is called.")

    uvicorn.run(app, host="127.0.0.1", port=8000)
