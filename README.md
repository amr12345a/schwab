# TradingView to Schwab Bridge

This project exposes a small FastAPI server that accepts TradingView webhook JSON and places Schwab equity market orders.

## TradingView payload

The server accepts the structure you showed, plus an optional `quantity` field and an optional `secret` field for webhook authentication.

Example alert message:

```json
{
  "action": "BUY",
  "symbol": "AAPL",
  "exchange": "NASDAQ",
  "price": 195.42,
  "ma_fast": "9",
  "ma_slow": "21",
  "ma_type": "EMA",
  "timeframe": "15",
  "time": "2026-04-18T10:30:00-0400",
  "quantity": 1,
  "secret": "replace-me"
}
```

## Configuration

Set these environment variables before starting the server:

- `SCHWAB_API_KEY`
- `SCHWAB_APP_SECRET`
- `SCHWAB_CALLBACK_URL` defaults to `https://127.0.0.1:8182/`
- `SCHWAB_TOKEN_PATH` defaults to `./token.json`
- `SCHWAB_ACCOUNT_HASH`
- `TRADINGVIEW_WEBHOOK_SECRET` optional, but recommended
- `DEFAULT_ORDER_QTY` defaults to `1`
- `DRY_RUN` defaults to `false`
- `SCHWAB_AUTH_MODE` defaults to `token_file`

`SCHWAB_AUTH_MODE=token_file` expects an existing Schwab token file. If you need to create one locally, use the Schwab login flow once and keep the token file private.

## Run

```bash
python3 -m app.main
```

## Example TradingView alert URL

Use your server URL as the webhook target, for example:

```text
https://your-server.example.com/webhook/tradingview?secret=replace-me
```

If you cannot use query parameters, include `secret` in the alert JSON instead.

## Safety notes

- Start with `DRY_RUN=true`.
- Make sure the Schwab account hash is correct.
- Test with a very small `DEFAULT_ORDER_QTY` before enabling live trading.
