from functools import lru_cache
from pathlib import Path

from schwab.auth import easy_client, client_from_token_file

from .config import get_settings


def _validate_required_settings() -> None:
    settings = get_settings()
    missing = []
    if not settings.schwab_api_key:
        missing.append("SCHWAB_API_KEY")
    if not settings.schwab_app_secret:
        missing.append("SCHWAB_APP_SECRET")
    if not settings.schwab_account_hash:
        missing.append("SCHWAB_ACCOUNT_HASH")
    if missing:
        raise RuntimeError("Missing required environment variables: " + ", ".join(missing))


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
        )

    if not token_path.exists():
        raise RuntimeError(
            f"Token file not found at {token_path}. Create a Schwab token first or set SCHWAB_AUTH_MODE=easy_client for local setup."
        )

    return client_from_token_file(
        token_path=str(token_path),
        api_key=settings.schwab_api_key,
        app_secret=settings.schwab_app_secret,
    )
