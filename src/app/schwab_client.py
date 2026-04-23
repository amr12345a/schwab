from functools import lru_cache
import json
from pathlib import Path
import time

from schwab.auth import easy_client, client_from_token_file

from .config import get_settings


def _validate_required_settings() -> None:
    settings = get_settings()
    missing = []
    if not settings.schwab_api_key:
        missing.append("SCHWAB_API_KEY")
    if not settings.schwab_app_secret:
        missing.append("SCHWAB_APP_SECRET")
    if missing:
        raise RuntimeError("Missing required environment variables: " + ", ".join(missing))


def _normalize_token_file_format(token_path: Path) -> None:
    if not token_path.exists():
        return

    with token_path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, dict):
        return

    if "creation_timestamp" in data and isinstance(data.get("token"), dict):
        return

    if "access_token" in data and "refresh_token" in data:
        wrapped_token = {
            "creation_timestamp": int(time.time()),
            "token": data,
        }
        with token_path.open("w", encoding="utf-8") as f:
            json.dump(wrapped_token, f)


@lru_cache(maxsize=1)
def get_client():
    settings = get_settings()
    _validate_required_settings()
    token_path = Path(settings.schwab_token_path)

    if settings.schwab_auth_mode == "easy_client":
        return easy_client(
            api_key=settings.schwab_api_key,
            app_secret=settings.schwab_app_secret,
            callback_url=settings.schwab_callback_url,
            token_path=str(token_path),
            interactive=False,
        )

    if not token_path.exists():
        raise RuntimeError(
            f"Token file not found at {token_path}. Create a Schwab token first or set SCHWAB_AUTH_MODE=easy_client for local setup."
        )

    _normalize_token_file_format(token_path)

    return client_from_token_file(
        token_path=str(token_path),
        api_key=settings.schwab_api_key,
        app_secret=settings.schwab_app_secret,
    )
