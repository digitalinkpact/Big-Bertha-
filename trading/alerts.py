"""Price alerts and monitoring for trading pairs.

Supports price-level alerts, volume spike detection, and periodic
market analysis reports.  Runs as an async background loop.
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable

from loguru import logger

from trading.client import BinanceUSClient


class AlertType(str, Enum):
    PRICE_ABOVE = "price_above"
    PRICE_BELOW = "price_below"
    VOLUME_SPIKE = "volume_spike"
    RSI_OVERSOLD = "rsi_oversold"
    RSI_OVERBOUGHT = "rsi_overbought"


@dataclass
class Alert:
    id: str
    symbol: str
    alert_type: AlertType
    threshold: float
    triggered: bool = False
    triggered_at: float | None = None
    message: str = ""
    one_shot: bool = True  # auto-remove after trigger


class AlertManager:
    """Manage and evaluate trading alerts."""

    def __init__(self):
        self._alerts: dict[str, Alert] = {}
        self._callbacks: list[Callable[[Alert], Any]] = []

    def add_alert(self, alert: Alert) -> None:
        self._alerts[alert.id] = alert
        logger.info(f"Alert added: {alert.id} — {alert.alert_type.value} {alert.symbol} @ {alert.threshold}")

    def remove_alert(self, alert_id: str) -> bool:
        return self._alerts.pop(alert_id, None) is not None

    def on_trigger(self, callback: Callable[[Alert], Any]) -> None:
        """Register a callback for when an alert fires."""
        self._callbacks.append(callback)

    def list_alerts(self) -> list[Alert]:
        return list(self._alerts.values())

    async def evaluate(self, client: BinanceUSClient) -> list[Alert]:
        """Check all alerts against current market data. Returns newly triggered alerts."""
        triggered: list[Alert] = []

        # Group alerts by symbol to minimise API calls
        symbols = {a.symbol for a in self._alerts.values() if not a.triggered}
        tickers: dict[str, dict] = {}
        for sym in symbols:
            try:
                tickers[sym] = await client.fetch_ticker(sym)
            except Exception as exc:
                logger.warning(f"Failed to fetch ticker for {sym}: {exc}")

        to_remove: list[str] = []
        for alert in self._alerts.values():
            if alert.triggered:
                continue
            ticker = tickers.get(alert.symbol)
            if not ticker:
                continue

            price = ticker["last"]
            fired = False

            if alert.alert_type == AlertType.PRICE_ABOVE and price >= alert.threshold:
                alert.message = f"{alert.symbol} hit ${price:.2f} (above ${alert.threshold:.2f})"
                fired = True
            elif alert.alert_type == AlertType.PRICE_BELOW and price <= alert.threshold:
                alert.message = f"{alert.symbol} hit ${price:.2f} (below ${alert.threshold:.2f})"
                fired = True
            elif alert.alert_type == AlertType.VOLUME_SPIKE:
                vol = ticker.get("quoteVolume", 0)
                if vol >= alert.threshold:
                    alert.message = f"{alert.symbol} volume spike: {vol:.0f} (threshold {alert.threshold:.0f})"
                    fired = True

            if fired:
                alert.triggered = True
                alert.triggered_at = time.time()
                triggered.append(alert)
                logger.info(f"ALERT TRIGGERED: {alert.message}")
                for cb in self._callbacks:
                    try:
                        result = cb(alert)
                        if asyncio.iscoroutine(result):
                            await result
                    except Exception as exc:
                        logger.error(f"Alert callback error: {exc}")
                if alert.one_shot:
                    to_remove.append(alert.id)

        for aid in to_remove:
            self._alerts.pop(aid, None)

        return triggered


class PortfolioMonitor:
    """Track portfolio value and risk metrics."""

    def __init__(self, client: BinanceUSClient):
        self._client = client
        self._snapshots: list[dict[str, Any]] = []

    async def snapshot(self) -> dict[str, Any]:
        """Take a portfolio snapshot."""
        balance = await self._client.fetch_balance()
        total_usd = balance.get("total", {}).get("USDT", 0.0)

        # Price non-USDT assets
        holdings: dict[str, dict] = {}
        for asset, amount in balance.get("total", {}).items():
            if amount and amount > 0 and asset != "USDT":
                try:
                    ticker = await self._client.fetch_ticker(f"{asset}/USDT")
                    usd_val = amount * ticker["last"]
                    holdings[asset] = {
                        "amount": amount,
                        "price_usd": ticker["last"],
                        "value_usd": usd_val,
                    }
                    total_usd += usd_val
                except Exception:
                    holdings[asset] = {"amount": amount, "price_usd": None, "value_usd": None}

        snap = {
            "timestamp": time.time(),
            "total_usd": total_usd,
            "usdt_balance": balance.get("total", {}).get("USDT", 0.0),
            "holdings": holdings,
        }
        self._snapshots.append(snap)
        return snap

    def pnl(self) -> dict[str, float] | None:
        """Calculate P&L from first to latest snapshot."""
        if len(self._snapshots) < 2:
            return None
        first = self._snapshots[0]["total_usd"]
        last = self._snapshots[-1]["total_usd"]
        return {
            "start_usd": first,
            "current_usd": last,
            "pnl_usd": last - first,
            "pnl_pct": ((last - first) / first * 100) if first else 0.0,
        }
