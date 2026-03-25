"""Nanobot agent tool for Binance.US trading operations.

Exposes market analysis, order placement, portfolio queries,
and alert management to the AI agent loop.
"""

from __future__ import annotations

import json
import os
import uuid
from typing import Any

from loguru import logger

from nanobot.agent.tools.base import Tool


def _json(obj: Any) -> str:
    """Safe JSON serialisation for tool responses."""
    def _default(o: Any) -> Any:
        if hasattr(o, "__dict__"):
            return {k: v for k, v in o.__dict__.items() if not k.startswith("_")}
        return str(o)
    return json.dumps(obj, indent=2, default=_default)


class TradingTool(Tool):
    """Unified trading tool for Binance.US via ccxt."""

    _client = None
    _alert_mgr = None
    _portfolio_mon = None

    @property
    def name(self) -> str:
        return "trading"

    @property
    def description(self) -> str:
        return (
            "Interact with Binance.US: market analysis, place orders, "
            "manage alerts, and query portfolio. "
            "Requires BINANCE_US_API_KEY and BINANCE_US_API_SECRET env vars."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "description": (
                        "One of: analyze, ticker, balance, buy, sell, "
                        "cancel_order, open_orders, portfolio, "
                        "add_alert, list_alerts, check_alerts, strategies"
                    ),
                },
                "symbol": {
                    "type": "string",
                    "description": "Trading pair, e.g. BTC/USDT",
                },
                "amount": {
                    "type": "number",
                    "description": "Quantity for buy/sell orders",
                },
                "price": {
                    "type": "number",
                    "description": "Limit price (omit for market orders)",
                },
                "order_type": {
                    "type": "string",
                    "description": "limit or market (default: limit)",
                },
                "order_id": {
                    "type": "string",
                    "description": "Order ID (for cancel_order)",
                },
                "alert_type": {
                    "type": "string",
                    "description": "price_above, price_below, or volume_spike",
                },
                "threshold": {
                    "type": "number",
                    "description": "Alert trigger threshold",
                },
                "timeframe": {
                    "type": "string",
                    "description": "Candle timeframe for analysis (1m,5m,15m,1h,4h,1d)",
                },
            },
            "required": ["action"],
        }

    def _ensure_client(self):
        """Lazy-init the trading client and helpers."""
        if self._client is not None:
            return

        api_key = os.environ.get("BINANCE_US_API_KEY", "")
        if not api_key:
            raise RuntimeError(
                "Trading not configured. Set BINANCE_US_API_KEY and "
                "BINANCE_US_API_SECRET environment variables."
            )

        from trading.client import BinanceUSClient
        from trading.alerts import AlertManager, PortfolioMonitor
        from trading.config import load_exchange_config

        cfg = load_exchange_config()
        TradingTool._client = BinanceUSClient(cfg)
        TradingTool._alert_mgr = AlertManager()
        TradingTool._portfolio_mon = PortfolioMonitor(TradingTool._client)

    async def execute(self, **kwargs: Any) -> str:
        action = kwargs.get("action", "").lower()
        symbol = kwargs.get("symbol", "BTC/USDT")

        try:
            self._ensure_client()
        except RuntimeError as e:
            return str(e)

        try:
            if action == "ticker":
                return await self._ticker(symbol)
            elif action == "analyze":
                return await self._analyze(symbol, kwargs.get("timeframe", "1h"))
            elif action == "balance":
                return await self._balance()
            elif action == "buy":
                return await self._buy(symbol, kwargs)
            elif action == "sell":
                return await self._sell(symbol, kwargs)
            elif action == "cancel_order":
                return await self._cancel(symbol, kwargs.get("order_id", ""))
            elif action == "open_orders":
                return await self._open_orders(symbol)
            elif action == "portfolio":
                return await self._portfolio()
            elif action == "add_alert":
                return self._add_alert(symbol, kwargs)
            elif action == "list_alerts":
                return self._list_alerts()
            elif action == "check_alerts":
                return await self._check_alerts()
            elif action == "strategies":
                return self._list_strategies()
            else:
                return (
                    f"Unknown action '{action}'. Available: analyze, ticker, "
                    "balance, buy, sell, cancel_order, open_orders, portfolio, "
                    "add_alert, list_alerts, check_alerts, strategies"
                )
        except Exception as exc:
            logger.error(f"Trading tool error ({action}): {exc}")
            return f"Error: {exc}"

    # -- action handlers -----------------------------------------------

    async def _ticker(self, symbol: str) -> str:
        t = await self._client.fetch_ticker(symbol)
        return _json({
            "symbol": symbol,
            "last": t.get("last"),
            "bid": t.get("bid"),
            "ask": t.get("ask"),
            "high": t.get("high"),
            "low": t.get("low"),
            "volume": t.get("quoteVolume"),
            "change_pct": t.get("percentage"),
        })

    async def _analyze(self, symbol: str, timeframe: str) -> str:
        from trading.analysis import full_analysis, ohlcv_to_df
        candles = await self._client.fetch_ohlcv(symbol, timeframe=timeframe, limit=100)
        df = ohlcv_to_df(candles)
        result = full_analysis(df)
        result["symbol"] = symbol
        result["timeframe"] = timeframe
        return _json(result)

    async def _balance(self) -> str:
        bal = await self._client.fetch_balance()
        # Filter to non-zero
        non_zero = {k: v for k, v in bal.get("total", {}).items() if v and v > 0}
        return _json({"balances": non_zero})

    async def _buy(self, symbol: str, params: dict) -> str:
        amount = params.get("amount")
        price = params.get("price")
        order_type = params.get("order_type", "limit")
        if not amount:
            return "Error: 'amount' is required for buy orders."
        if order_type == "market":
            order = await self._client.create_market_buy(symbol, amount, estimated_price=price)
        else:
            if not price:
                return "Error: 'price' is required for limit buy orders."
            order = await self._client.create_limit_buy(symbol, amount, price)
        return _json({"status": "order_placed", "order_id": order.get("id"), "symbol": symbol})

    async def _sell(self, symbol: str, params: dict) -> str:
        amount = params.get("amount")
        price = params.get("price")
        order_type = params.get("order_type", "limit")
        if not amount:
            return "Error: 'amount' is required for sell orders."
        if order_type == "market":
            order = await self._client.create_market_sell(symbol, amount)
        else:
            if not price:
                return "Error: 'price' is required for limit sell orders."
            order = await self._client.create_limit_sell(symbol, amount, price)
        return _json({"status": "order_placed", "order_id": order.get("id"), "symbol": symbol})

    async def _cancel(self, symbol: str, order_id: str) -> str:
        if not order_id:
            return "Error: 'order_id' is required to cancel an order."
        result = await self._client.cancel_order(order_id, symbol)
        return _json({"status": "cancelled", "order_id": order_id})

    async def _open_orders(self, symbol: str) -> str:
        orders = await self._client.fetch_open_orders(symbol)
        return _json({"open_orders": len(orders), "orders": orders})

    async def _portfolio(self) -> str:
        snap = await self._portfolio_mon.snapshot()
        pnl = self._portfolio_mon.pnl()
        return _json({"snapshot": snap, "pnl": pnl})

    def _add_alert(self, symbol: str, params: dict) -> str:
        from trading.alerts import Alert, AlertType
        at_str = params.get("alert_type", "price_above")
        try:
            at = AlertType(at_str)
        except ValueError:
            return f"Error: Invalid alert_type '{at_str}'. Use: price_above, price_below, volume_spike"
        threshold = params.get("threshold")
        if threshold is None:
            return "Error: 'threshold' is required for alerts."
        alert = Alert(
            id=f"alert-{uuid.uuid4().hex[:8]}",
            symbol=symbol,
            alert_type=at,
            threshold=threshold,
        )
        self._alert_mgr.add_alert(alert)
        return _json({"status": "alert_created", "id": alert.id, "symbol": symbol, "type": at_str, "threshold": threshold})

    def _list_alerts(self) -> str:
        alerts = self._alert_mgr.list_alerts()
        return _json({"alerts": [{"id": a.id, "symbol": a.symbol, "type": a.alert_type.value, "threshold": a.threshold, "triggered": a.triggered} for a in alerts]})

    async def _check_alerts(self) -> str:
        triggered = await self._alert_mgr.evaluate(self._client)
        return _json({"triggered": [{"id": a.id, "message": a.message} for a in triggered]})

    def _list_strategies(self) -> str:
        from trading.strategies import STRATEGIES
        return _json({"available_strategies": list(STRATEGIES.keys())})
