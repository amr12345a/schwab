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
- `SCHWAB_ACCOUNT_HASH` optional; if omitted, choose an account at runtime through `/trader/v1/accounts`
- `SCHWAB_PAPER_ACCOUNT_HASH` and `SCHWAB_REAL_ACCOUNT_HASH` optional; if both are set, the launcher asks which account to use
- `TRADINGVIEW_WEBHOOK_SECRET` optional, but recommended
- `DEFAULT_ORDER_QTY` defaults to `1`
- `DRY_RUN` defaults to `false`
- `SCHWAB_AUTH_MODE` defaults to `token_file`

`SCHWAB_AUTH_MODE=token_file` expects an existing Schwab token file. If you need to create one locally, use the Schwab login flow once and keep the token file private.

Use `GET /trader/v1/accounts` to see the linked Schwab accounts. Pass `account_hash=<hashValue>` to that endpoint to set the active account for subsequent trades.

To send a direct test order to Schwab from Python, run [scripts/test_order.py](scripts/test_order.py):

```bash
python scripts/test_order.py --account-hash your-account-hash --symbol AAPL --quantity 1 --dry-run
```

Remove `--dry-run` only when you are ready to submit a real order.

If you set both `SCHWAB_PAPER_ACCOUNT_HASH` and `SCHWAB_REAL_ACCOUNT_HASH`, start the app from the terminal and it will prompt you to choose paper or real before the server comes up.

## Run

```bash
python3 -m app.main
```

## Nginx

If you want nginx in front of the app, keep FastAPI bound to `127.0.0.1:8000` and let nginx listen on `80` or `443`.

A sample reverse-proxy config is provided in [nginx/nginx.conf](nginx/nginx.conf). It forwards all requests, including `/webhook/tradingview` and `/trader/v1/accounts`, to the app server.

To test the nginx entry point directly, request `GET /__nginx_test` on the public port:

```bash
curl http://127.0.0.1/__nginx_test
```

That should return `nginx entry ok`.

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
