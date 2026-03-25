"""Trading strategies for Binance.US.

Each strategy is a callable that takes market data and returns
a list of suggested actions (buy/sell/hold with parameters).
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from loguru import logger

from trading.analysis import full_analysis, ohlcv_to_df
from trading.client import BinanceUSClient


class Action(str, Enum):
    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"


@dataclass
class TradeSignal:
    action: Action
    symbol: str
    amount: float | None = None
    price: float | None = None
    reason: str = ""
    confidence: float = 0.0  # 0.0 – 1.0


# ------------------------------------------------------------------
# Dollar-Cost Averaging (DCA)
# ------------------------------------------------------------------

class DCAStrategy:
    """Buy a fixed USD amount at regular intervals regardless of price."""

    def __init__(self, amount_usd: float = 50.0, interval_seconds: int = 86400):
        self.amount_usd = amount_usd
        self.interval = interval_seconds
        self._last_buy_ts: float = 0.0

    def should_execute(self) -> bool:
        return (time.time() - self._last_buy_ts) >= self.interval

    async def evaluate(self, client: BinanceUSClient, symbol: str = "BTC/USDT") -> TradeSignal:
        if not self.should_execute():
            return TradeSignal(
                action=Action.HOLD, symbol=symbol,
                reason=f"DCA interval not reached ({self.interval}s)"
            )

        ticker = await client.fetch_ticker(symbol)
        price = ticker["last"]
        qty = self.amount_usd / price

        self._last_buy_ts = time.time()
        return TradeSignal(
            action=Action.BUY, symbol=symbol,
            amount=qty, price=price,
            reason=f"DCA: ${self.amount_usd} at ${price:.2f}",
            confidence=0.9,
        )


# ------------------------------------------------------------------
# Grid Trading
# ------------------------------------------------------------------

class GridStrategy:
    """Place buy/sell orders at evenly spaced price levels."""

    def __init__(
        self,
        lower: float,
        upper: float,
        grids: int = 10,
        total_usd: float = 500.0,
    ):
        self.lower = lower
        self.upper = upper
        self.grids = grids
        self.total_usd = total_usd
        self.grid_levels = self._calc_levels()

    def _calc_levels(self) -> list[float]:
        step = (self.upper - self.lower) / self.grids
        return [round(self.lower + i * step, 2) for i in range(self.grids + 1)]

    async def evaluate(self, client: BinanceUSClient, symbol: str = "BTC/USDT") -> list[TradeSignal]:
        ticker = await client.fetch_ticker(symbol)
        price = ticker["last"]
        signals: list[TradeSignal] = []
        usd_per_grid = self.total_usd / self.grids

        for level in self.grid_levels:
            qty = usd_per_grid / level
            if level < price:
                signals.append(TradeSignal(
                    action=Action.BUY, symbol=symbol,
                    amount=qty, price=level,
                    reason=f"Grid buy at ${level:.2f}",
                    confidence=0.7,
                ))
            elif level > price:
                signals.append(TradeSignal(
                    action=Action.SELL, symbol=symbol,
                    amount=qty, price=level,
                    reason=f"Grid sell at ${level:.2f}",
                    confidence=0.7,
                ))

        return signals


# ------------------------------------------------------------------
# Momentum / Swing (indicator-based)
# ------------------------------------------------------------------

class MomentumStrategy:
    """Use RSI + MACD + Bollinger Bands to identify entry/exit points."""

    def __init__(self, position_usd: float = 200.0):
        self.position_usd = position_usd

    async def evaluate(self, client: BinanceUSClient, symbol: str = "BTC/USDT") -> TradeSignal:
        candles = await client.fetch_ohlcv(symbol, timeframe="1h", limit=100)
        df = ohlcv_to_df(candles)
        result = full_analysis(df)

        price = result["price"]
        signal = result["signal"]
        score = result["score"]
        reasons = "; ".join(result["reasons"])

        confidence = min(1.0, abs(score) / 5.0)

        if signal in ("STRONG_BUY", "BUY"):
            qty = self.position_usd / price
            return TradeSignal(
                action=Action.BUY, symbol=symbol,
                amount=qty, price=price,
                reason=f"Momentum {signal}: {reasons}",
                confidence=confidence,
            )
        elif signal in ("STRONG_SELL", "SELL"):
            return TradeSignal(
                action=Action.SELL, symbol=symbol,
                price=price,
                reason=f"Momentum {signal}: {reasons}",
                confidence=confidence,
            )
        else:
            return TradeSignal(
                action=Action.HOLD, symbol=symbol,
                reason=f"Momentum NEUTRAL: {reasons}",
                confidence=confidence,
            )


# ------------------------------------------------------------------
# Strategy factory
# ------------------------------------------------------------------

STRATEGIES: dict[str, type] = {
    "dca": DCAStrategy,
    "grid": GridStrategy,
    "momentum": MomentumStrategy,
    "swing": MomentumStrategy,  # alias
}


def get_strategy(name: str, **kwargs: Any):
    """Get a strategy by name with optional config overrides."""
    cls = STRATEGIES.get(name.lower())
    if cls is None:
        raise ValueError(f"Unknown strategy '{name}'. Available: {list(STRATEGIES.keys())}")
    return cls(**kwargs)
