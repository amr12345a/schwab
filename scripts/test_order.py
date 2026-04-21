from __future__ import annotations

import argparse
import json
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


def _request_json(method: str, url: str, payload: dict | None = None) -> dict:
    data = None
    headers = {}

    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"

    request = Request(url, data=data, headers=headers, method=method)

    try:
        with urlopen(request) as response:
            body = response.read().decode("utf-8")
            return json.loads(body) if body else {}
    except HTTPError as exc:
        body = exc.read().decode("utf-8")
        raise RuntimeError(f"HTTP {exc.code}: {body or exc.reason}") from exc
    except URLError as exc:
        raise RuntimeError(f"Request failed: {exc.reason}") from exc


def main() -> int:
    parser = argparse.ArgumentParser(description="Select a Schwab account and submit a test order")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000", help="Base URL for the FastAPI app")
    parser.add_argument("--account-hash", help="Account hash to activate before placing the order")
    parser.add_argument("--action", choices=["BUY", "SELL"], default="BUY")
    parser.add_argument("--symbol", default="AAPL")
    parser.add_argument("--quantity", type=int, default=1)
    parser.add_argument("--dry-run", action="store_true", help="Validate the order path without submitting")
    args = parser.parse_args()

    base_url = args.base_url.rstrip("/")

    if args.account_hash:
        account_query = urlencode({"account_hash": args.account_hash})
        account_response = _request_json("GET", f"{base_url}/trader/v1/accounts?{account_query}")
    else:
        account_response = _request_json("GET", f"{base_url}/trader/v1/accounts")

    print(json.dumps(account_response, indent=2))

    test_order_response = _request_json(
        "POST",
        f"{base_url}/trader/v1/accounts/test-order",
        payload={
            "action": args.action,
            "symbol": args.symbol,
            "quantity": args.quantity,
            "dry_run": args.dry_run,
        },
    )

    print(json.dumps(test_order_response, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())