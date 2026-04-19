from datetime import datetime
from decimal import Decimal
import re
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class TradingViewSignal(BaseModel):
    action: Literal["BUY", "SELL"]
    symbol: str = Field(min_length=1)
    exchange: str | None = None
    price: Decimal | None = None
    ma_fast: str | None = None
    ma_slow: str | None = None
    ma_type: str | None = None
    timeframe: str | None = None
    time: datetime | None = None
    quantity: int | None = Field(default=None, ge=1)
    secret: str | None = None

    @field_validator("symbol")
    @classmethod
    def normalize_symbol(cls, value: str) -> str:
        return value.strip().upper()

    @field_validator("time", mode="before")
    @classmethod
    def parse_time(cls, value):
        if value in (None, ""):
            return None
        if isinstance(value, str):
            normalized = re.sub(r"([+-]\d{2})(\d{2})$", r"\1:\2", value)
            if normalized.endswith("Z"):
                normalized = normalized[:-1] + "+00:00"
            return normalized
        return value


class TradeResult(BaseModel):
    ok: bool
    dry_run: bool
    action: str
    symbol: str
    quantity: int
    account_hash: str
    order_id: str | None = None
    message: str
