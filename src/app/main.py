from pathlib import Path
import sys

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi import FastAPI, HTTPException, Request, status

from app.config import get_settings
from app.models import TradeResult, TradingViewSignal
from app.trading import execute_signal

app = FastAPI(title="TradingView to Schwab Bridge", version="0.1.0")


@app.get("/health")
def health():
    return {"status": "ok"}


def _extract_secret(request: Request, signal: TradingViewSignal) -> str | None:
    query_secret = request.query_params.get("secret")
    if query_secret:
        return query_secret
    return signal.secret


@app.post("/webhook/tradingview", response_model=TradeResult)
def tradingview_webhook(signal: TradingViewSignal, request: Request):
    settings = get_settings()
    if settings.tradingview_webhook_secret:
        incoming_secret = _extract_secret(request, signal)
        if incoming_secret != settings.tradingview_webhook_secret:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid webhook secret")

    try:
        return execute_signal(signal)
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=False)
