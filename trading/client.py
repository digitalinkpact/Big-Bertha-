"""Binance.US exchange client — thin wrapper around ccxt.

Handles connection, authentication, and rate limiting.
All credentials come from ExchangeConfig (env vars).
"""

from __future__ import annotations

import time
from typing import Any

import ccxt
from loguru import logger

from trading.config import ExchangeConfig, load_exchange_config


class BinanceUSClient:
    """Thread-safe Binance.US client with rate-limit tracking."""

    def __init__(self, config: ExchangeConfig | None = None):
        self._cfg = config or load_exchange_config()
        self._exchange = ccxt.binanceus({
            "apiKey": self._cfg.api_key,
            "secret": self._cfg.api_secret,
            "enableRateLimit": self._cfg.rate_limit,
            "options": {"defaultType": "spot"},
        })
        if self._cfg.sandbox:
            self._exchange.set_sandbox_mode(True)
            logger.info("Binance.US client initialised in SANDBOX mode")
        else:
            logger.info("Binance.US client initialised (live)")

        self._daily_spent_usd: float = 0.0
        self._daily_reset_ts: float = 0.0

    # ------------------------------------------------------------------
    # Market data (read-only, no auth needed for public endpoints)
    # ------------------------------------------------------------------

    async def fetch_ticker(self, symbol: str = "BTC/USDT") -> dict[str, Any]:
        """Get current ticker for a symbol."""
        return self._exchange.fetch_ticker(symbol)

    async def fetch_ohlcv(
        self, symbol: str = "BTC/USDT", timeframe: str = "1h", limit: int = 100
    ) -> list[list]:
        """Fetch OHLCV candles."""
        return self._exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)

    async def fetch_order_book(self, symbol: str = "BTC/USDT", limit: int = 20) -> dict:
        """Fetch order book depth."""
        return self._exchange.fetch_order_book(symbol, limit=limit)

    async def fetch_markets(self) -> list[dict]:
        """List available markets on Binance.US."""
        return self._exchange.fetch_markets()

    # ------------------------------------------------------------------
    # Account (requires auth)
    # ------------------------------------------------------------------

    async def fetch_balance(self) -> dict[str, Any]:
        """Get account balances."""
        return self._exchange.fetch_balance()

    async def fetch_open_orders(self, symbol: str | None = None) -> list[dict]:
        """Get open orders, optionally filtered by symbol."""
        return self._exchange.fetch_open_orders(symbol)

    async def fetch_my_trades(self, symbol: str = "BTC/USDT", limit: int = 50) -> list[dict]:
        """Fetch recent trades for the account."""
        return self._exchange.fetch_my_trades(symbol, limit=limit)

    # ------------------------------------------------------------------
    # Order placement (with daily-limit guard)
    # ------------------------------------------------------------------

    def _check_daily_limit(self, cost_usd: float) -> None:
        """Enforce daily spending limit."""
        now = time.time()
        if now - self._daily_reset_ts > 86400:
            self._daily_spent_usd = 0.0
            self._daily_reset_ts = now

        if self._daily_spent_usd + cost_usd > self._cfg.daily_limit_usd:
            raise RuntimeError(
                f"Daily trading limit reached "
                f"(${self._daily_spent_usd:.2f} / ${self._cfg.daily_limit_usd:.2f})"
            )

    async def create_limit_buy(
        self, symbol: str, amount: float, price: float
    ) -> dict[str, Any]:
        """Place a limit buy order."""
        cost = amount * price
        self._check_daily_limit(cost)
        order = self._exchange.create_limit_buy_order(symbol, amount, price)
        self._daily_spent_usd += cost
        logger.info(f"LIMIT BUY {symbol} qty={amount} @ {price} => {order['id']}")
        return order

    async def create_limit_sell(
        self, symbol: str, amount: float, price: float
    ) -> dict[str, Any]:
        """Place a limit sell order."""
        order = self._exchange.create_limit_sell_order(symbol, amount, price)
        logger.info(f"LIMIT SELL {symbol} qty={amount} @ {price} => {order['id']}")
        return order

    async def create_market_buy(
        self, symbol: str, amount: float, estimated_price: float | None = None
    ) -> dict[str, Any]:
        """Place a market buy order."""
        if estimated_price:
            self._check_daily_limit(amount * estimated_price)
        order = self._exchange.create_market_buy_order(symbol, amount)
        if estimated_price:
            self._daily_spent_usd += amount * estimated_price
        logger.info(f"MARKET BUY {symbol} qty={amount} => {order['id']}")
        return order

    async def create_market_sell(self, symbol: str, amount: float) -> dict[str, Any]:
        """Place a market sell order."""
        order = self._exchange.create_market_sell_order(symbol, amount)
        logger.info(f"MARKET SELL {symbol} qty={amount} => {order['id']}")
        return order

    async def cancel_order(self, order_id: str, symbol: str) -> dict[str, Any]:
        """Cancel an open order."""
        result = self._exchange.cancel_order(order_id, symbol)
        logger.info(f"CANCELLED order {order_id} on {symbol}")
        return result

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @property
    def daily_remaining_usd(self) -> float:
        now = time.time()
        if now - self._daily_reset_ts > 86400:
            return self._cfg.daily_limit_usd
        return max(0.0, self._cfg.daily_limit_usd - self._daily_spent_usd)

    def close(self) -> None:
        """Close the underlying connection."""
        self._exchange.close()
