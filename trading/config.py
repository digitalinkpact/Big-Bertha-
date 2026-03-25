"""Secure configuration for exchange API credentials.

All secrets are read from environment variables — never hardcoded.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

# Load .env from workspace root if present
_ROOT = Path(__file__).resolve().parent.parent
_env_file = _ROOT / ".env"
if _env_file.exists():
    load_dotenv(_env_file)


@dataclass(frozen=True)
class ExchangeConfig:
    """Immutable exchange connection configuration."""

    api_key: str
    api_secret: str
    base_url: str = "https://api.binance.us"
    sandbox: bool = False
    rate_limit: bool = True

    # Trading constraints
    daily_limit_usd: float = 1000.0
    max_position_pct: float = 0.10  # max 10 % of portfolio per position
    stop_loss_pct: float = 0.05     # default 5 % stop-loss
    take_profit_pct: float = 0.10   # default 10 % take-profit

    def __post_init__(self):
        if not self.api_key or not self.api_secret:
            raise ValueError(
                "Exchange API key and secret are required. "
                "Set BINANCE_US_API_KEY and BINANCE_US_API_SECRET env vars."
            )

    def __repr__(self) -> str:
        """Never leak secrets in logs/repr."""
        return (
            f"ExchangeConfig(base_url={self.base_url!r}, "
            f"sandbox={self.sandbox}, key=***{self.api_key[-4:]})"
        )


@dataclass
class TradingPreferences:
    """User-configurable trading preferences."""

    primary_pair: str = "BTC/USDT"
    risk_tolerance: str = "medium"  # low / medium / high
    strategy: str = "dca"           # dca / grid / swing / momentum
    daily_limit_usd: float = 1000.0
    stop_loss_pct: float = 0.05
    take_profit_pct: float = 0.10
    pairs: list[str] = field(default_factory=lambda: ["BTC/USDT", "ETH/USDT"])


def load_exchange_config() -> ExchangeConfig:
    """Load exchange config from environment variables."""
    return ExchangeConfig(
        api_key=os.environ.get("BINANCE_US_API_KEY", ""),
        api_secret=os.environ.get("BINANCE_US_API_SECRET", ""),
        base_url=os.environ.get("BINANCE_US_BASE_URL", "https://api.binance.us"),
        sandbox=os.environ.get("BINANCE_US_SANDBOX", "false").lower() in ("true", "1"),
        daily_limit_usd=float(os.environ.get("TRADING_DAILY_LIMIT", "1000")),
        stop_loss_pct=float(os.environ.get("TRADING_STOP_LOSS_PCT", "0.05")),
        take_profit_pct=float(os.environ.get("TRADING_TAKE_PROFIT_PCT", "0.10")),
    )


def load_trading_preferences() -> TradingPreferences:
    """Load trading preferences from environment variables."""
    pairs_raw = os.environ.get("TRADING_PAIRS", "BTC/USDT,ETH/USDT")
    return TradingPreferences(
        primary_pair=os.environ.get("TRADING_PRIMARY_PAIR", "BTC/USDT"),
        risk_tolerance=os.environ.get("TRADING_RISK_TOLERANCE", "medium"),
        strategy=os.environ.get("TRADING_STRATEGY", "dca"),
        daily_limit_usd=float(os.environ.get("TRADING_DAILY_LIMIT", "1000")),
        stop_loss_pct=float(os.environ.get("TRADING_STOP_LOSS_PCT", "0.05")),
        take_profit_pct=float(os.environ.get("TRADING_TAKE_PROFIT_PCT", "0.10")),
        pairs=[p.strip() for p in pairs_raw.split(",") if p.strip()],
    )
