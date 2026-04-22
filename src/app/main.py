from pathlib import Path
import os
import sys
from threading import Lock
from urllib.parse import parse_qs, urlencode, urlparse

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from fastapi import FastAPI, HTTPException, Request, status, Form
from fastapi.responses import HTMLResponse, RedirectResponse
import requests

from app.config import get_settings
from app.models import TestOrderRequest, TradeResult, TradingViewSignal
from app.schwab_client import get_client
from app.trading import execute_signal, execute_test_order

app = FastAPI(title="TradingView to Schwab Bridge", version="0.1.0")
_account_hash_lock = Lock()
_active_account_hash: str | None = None

# --- Web UI Templates ---
def _get_html_wrapper(content: str):
    return f"""
    <html>
        <head>
            <title>Schwab Bridge Dashboard</title>
            <style>
                body {{ font-family: sans-serif; margin: 40px; line-height: 1.6; max-width: 800px; }}
                .card {{ border: 1px solid #ddd; padding: 20px; border-radius: 8px; box-shadow: 2px 2px 10px #eee; }}
                .btn {{ background: #007bff; color: white; padding: 10px 20px; text-decoration: none; border-radius: 4px; display: inline-block; border: none; cursor: pointer; }}
                .status {{ font-weight: bold; color: green; }}
                input[type="text"] {{ width: 100%; padding: 10px; margin: 10px 0; }}
            </style>
        </head>
        <body>
            <div class="card">{content}</div>
        </body>
    </html>
    """

@app.get("/", response_class=HTMLResponse)
def dashboard():
    settings = get_settings()
    active = _get_active_account_hash()
    
    token_exists = Path(settings.schwab_token_path).exists()
    status_msg = f"Connected to Account: <span class='status'>{active}</span>" if active else "Not Connected"
    
    content = f"""
        <h1>Schwab Bridge Dashboard</h1>
        <p>Status: {status_msg}</p>
        <hr/>
        <h3>Step 1: Authenticate</h3>
        {"<p style='color: green;'>✓ Token Found</p>" if token_exists else "<p style='color: red;'>× No Token Found</p>"}
        <a class="btn" href="/auth/login">Login to Schwab</a>
        <p><small>If you are redirected to a broken '127.0.0.1' page, copy the whole URL and paste it below.</small></p>
        <form action="/auth/callback-manual" method="post">
            <input type="text" name="url" placeholder="Paste the redirected 127.0.0.1 URL here" required/>
            <button class="btn" type="submit">Complete Auth</button>
        </form>
        <hr/>
        <h3>Step 2: Select Account</h3>
        <a class="btn" style="background: #28a745;" href="/trader/v1/accounts/ui">View & Select Accounts</a>
    """
    return _get_html_wrapper(content)

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

# --- Auth Routes ---
@app.get("/auth/login")
def auth_login():
    settings = get_settings()
    if not settings.schwab_api_key:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Missing SCHWAB_API_KEY")

    params = {
        "client_id": settings.schwab_api_key,
        "redirect_uri": settings.schwab_callback_url,
        "response_type": "code",
    }

    scope = os.getenv("SCHWAB_SCOPE", "").strip()
    if scope:
        params["scope"] = scope

    auth_url = f"https://api.schwabapi.com/v1/oauth/authorize?{urlencode(params)}"
    return RedirectResponse(auth_url)

@app.post("/auth/callback-manual")
def auth_callback_manual(url: str = Form(...)):
    import time
    settings = get_settings()
    
    parsed = urlparse(url)
    params = parse_qs(parsed.query)

    if "error" in params:
        detail = params.get("error_description", [""])[0]
        raise HTTPException(status_code=400, detail=f"OAuth error: {params['error'][0]} {detail}".strip())

    if "code" not in params:
        raise HTTPException(status_code=400, detail="No code found in URL")
    
    code = params["code"][0]
    
    # Exchange
    token_resp = requests.post(
        "https://api.schwabapi.com/v1/oauth/token",
        data={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": settings.schwab_callback_url,
            "client_id": settings.schwab_api_key,
            "client_secret": settings.schwab_app_secret,
        },
        timeout=30,
    )

    try:
        token_resp.raise_for_status()
    except requests.HTTPError as exc:
        detail = token_resp.text.strip() if token_resp.text else str(exc)
        raise HTTPException(status_code=502, detail=f"Token exchange failed: {detail}") from exc

    token_data = token_resp.json()
    token_data["expires_at"] = time.time() + token_data.get("expires_in", 3600)
    
    with open(settings.schwab_token_path, "w") as f:
        import json
        json.dump(token_data, f)
    
    return RedirectResponse("/", status_code=status.HTTP_302_FOUND)

@app.get("/trader/v1/accounts/ui", response_class=HTMLResponse)
def trader_accounts_ui():
    try:
        client = get_client()
        response = client.get_account_numbers()
        accounts = response.json()
        
        list_html = ""
        for acc in accounts:
            h = acc.get("hashValue")
            n = acc.get("accountNumber")
            list_html += f"<li>{n} | <a href='/trader/v1/accounts?account_hash={h}'>Select this account</a></li>"
        
        content = f"""
            <h1>Select Your Account</h1>
            <ul>{list_html}</ul>
            <br/><a href="/">Back to Dashboard</a>
        """
        return _get_html_wrapper(content)
    except Exception as e:
        return _get_html_wrapper(f"<h1>Error</h1><p>{str(e)}</p><a href='/'>Back</a>")


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
    
    # If not in list, force it anyway (useful for single accounts)
    os.environ["SCHWAB_ACCOUNT_HASH"] = account_hash
    get_settings.cache_clear()
    return account_hash


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
            return RedirectResponse("/")
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

    _initialize_active_account_hash()
    
    active = _get_active_account_hash()
    if active:
        print(f"READY: Server starting. Active Account: {active}")
    else:
        print("READY: No account selected. Webhooks will fail until an account is chosen via API.")

    uvicorn.run(app, host="127.0.0.1", port=8000)
