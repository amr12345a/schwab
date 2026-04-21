from functools import lru_cache
from pathlib import Path
from typing import Literal
import os

from pydantic import BaseModel, Field


class Settings(BaseModel):
    schwab_api_key: str = Field(default="", alias="SCHWAB_API_KEY")
    schwab_app_secret: str = Field(default="", alias="SCHWAB_APP_SECRET")
    schwab_callback_url: str = Field(default="http://127.0.0.1:8000/auth/callback", alias="SCHWAB_CALLBACK_URL")
    schwab_token_path: Path = Field(default=Path("token.json"), alias="SCHWAB_TOKEN_PATH")
    schwab_account_hash: str = Field(default="", alias="SCHWAB_ACCOUNT_HASH")
    schwab_auth_mode: Literal["token_file", "easy_client"] = Field(default="token_file", alias="SCHWAB_AUTH_MODE")
    tradingview_webhook_secret: str | None = Field(default=None, alias="TRADINGVIEW_WEBHOOK_SECRET")
    default_order_qty: int = Field(default=1, alias="DEFAULT_ORDER_QTY", ge=1)
    dry_run: bool = Field(default=False, alias="DRY_RUN")

    class Config:
        populate_by_name = True


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    data = {
        "SCHWAB_API_KEY": os.getenv("SCHWAB_API_KEY", ""),
        "SCHWAB_APP_SECRET": os.getenv("SCHWAB_APP_SECRET", ""),
        "SCHWAB_CALLBACK_URL": os.getenv("SCHWAB_CALLBACK_URL", "http://127.0.0.1:8000/auth/callback"),
        "SCHWAB_TOKEN_PATH": os.getenv("SCHWAB_TOKEN_PATH", "token.json"),
        "SCHWAB_ACCOUNT_HASH": os.getenv("SCHWAB_ACCOUNT_HASH", ""),
        "SCHWAB_AUTH_MODE": os.getenv("SCHWAB_AUTH_MODE", "token_file"),
        "TRADINGVIEW_WEBHOOK_SECRET": os.getenv("TRADINGVIEW_WEBHOOK_SECRET"),
        "DEFAULT_ORDER_QTY": os.getenv("DEFAULT_ORDER_QTY", "1"),
        "DRY_RUN": os.getenv("DRY_RUN", "false"),
    }
    return Settings.model_validate(data)
