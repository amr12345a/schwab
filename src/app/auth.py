import os
import json
import requests
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs
from dotenv import load_dotenv

load_dotenv()


CLIENT_ID="cYVGMpfYMIKAqlTX6dyxlypBAa0ugdGYNAJedba2Qi0iG0XA"
CLIENT_SECRET="G2KGHcQMNiR1qhaiAPn0XupebuoGJlGcU6W8iC9qRnnF6WEkt22HFVHTrdaq3cP1"
REDIRECT_URI = os.getenv("SCHWAB_REDIRECT_URI", "http://127.0.0.1:8080")
TOKEN_FILE = os.getenv("SCHWAB_TOKEN_FILE", "token.json")

AUTH_URL = "https://api.schwabapi.com/v1/oauth/authorize"
TOKEN_URL = "https://api.schwabapi.com/v1/oauth/token"


# -----------------------------
# Save token
# -----------------------------
def save_token(token_data):
    with open(TOKEN_FILE, "w") as f:
        json.dump(token_data, f, indent=2)
    print(f"[OK] Token saved to {TOKEN_FILE}")


# -----------------------------
# HTTP handler for callback
# -----------------------------
class CallbackHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)

        if "code" not in params:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b"Missing code")
            return

        code = params["code"][0]

        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Auth successful. You can close this window.")

        # Exchange code for token
        token = exchange_code(code)
        save_token(token)

        print("\n[DONE] Authentication complete.")
        print("[INFO] You can now stop this server.")

        # Stop server after success
        os._exit(0)


# -----------------------------
# Exchange auth code for token
# -----------------------------
def exchange_code(code):
    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": REDIRECT_URI,
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
    }

    r = requests.post(TOKEN_URL, data=data)
    r.raise_for_status()

    token = r.json()

    # add expiry timestamp
    import time
    token["expires_at"] = time.time() + token.get("expires_in", 3600)

    return token


# -----------------------------
# Start local server
# -----------------------------
def start_server():
    server = HTTPServer(("127.0.0.1", 8080), CallbackHandler)
    print("[INFO] Listening on http://127.0.0.1:8080")
    server.serve_forever()


# -----------------------------
# Main OAuth flow
# -----------------------------
def main():
    if not CLIENT_ID or not CLIENT_SECRET:
        raise RuntimeError("Missing SCHWAB_CLIENT_ID or SCHWAB_CLIENT_SECRET")

    auth_url = (
        f"{AUTH_URL}"
        f"?client_id={CLIENT_ID}"
        f"&redirect_uri={REDIRECT_URI}"
        "&response_type=code"
    )

    print("[INFO] Copy and paste this URL into your local browser to authenticate:")
    print(auth_url)
    start_server()


if __name__ == "__main__":
    main()