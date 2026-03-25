"""Tests for the trading subsystem — config, analysis, strategies, alerts."""

from __future__ import annotations

import os
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

import numpy as np
import pandas as pd


class TestExchangeConfig(unittest.TestCase):
    """Test secure config loading."""

    def test_config_requires_keys(self):
        from trading.config import ExchangeConfig
        with self.assertRaises(ValueError):
            ExchangeConfig(api_key="", api_secret="")

    def test_config_repr_hides_secret(self):
        from trading.config import ExchangeConfig
        cfg = ExchangeConfig(api_key="abcdef1234", api_secret="secret9999")
        r = repr(cfg)
        self.assertNotIn("secret9999", r)
        self.assertNotIn("abcdef1234", r)
        self.assertIn("***1234", r)

    @patch.dict(os.environ, {
        "BINANCE_US_API_KEY": "test_key_1234",
        "BINANCE_US_API_SECRET": "test_secret",
        "TRADING_DAILY_LIMIT": "500",
    })
    def test_load_from_env(self):
        from trading.config import load_exchange_config
        cfg = load_exchange_config()
        self.assertEqual(cfg.api_key, "test_key_1234")
        self.assertEqual(cfg.daily_limit_usd, 500.0)

    @patch.dict(os.environ, {
        "TRADING_PRIMARY_PAIR": "ETH/USDT",
        "TRADING_PAIRS": "ETH/USDT,SOL/USDT",
        "TRADING_RISK_TOLERANCE": "high",
    })
    def test_load_preferences(self):
        from trading.config import load_trading_preferences
        prefs = load_trading_preferences()
        self.assertEqual(prefs.primary_pair, "ETH/USDT")
        self.assertEqual(prefs.risk_tolerance, "high")
        self.assertIn("SOL/USDT", prefs.pairs)


class TestAnalysis(unittest.TestCase):
    """Test technical analysis on synthetic data."""

    def _make_candles(self, n: int = 100) -> list[list]:
        """Generate synthetic OHLCV data."""
        import time
        base_ts = int(time.time() * 1000) - n * 3600_000
        candles = []
        price = 50000.0
        for i in range(n):
            ts = base_ts + i * 3600_000
            change = np.random.normal(0, 200)
            o = price
            c = price + change
            h = max(o, c) + abs(np.random.normal(0, 100))
            l = min(o, c) - abs(np.random.normal(0, 100))
            v = abs(np.random.normal(1000, 500))
            candles.append([ts, o, h, l, c, v])
            price = c
        return candles

    def test_ohlcv_to_df(self):
        from trading.analysis import ohlcv_to_df
        candles = self._make_candles(50)
        df = ohlcv_to_df(candles)
        self.assertEqual(len(df), 50)
        self.assertIn("close", df.columns)

    def test_full_analysis_returns_signal(self):
        from trading.analysis import ohlcv_to_df, full_analysis
        candles = self._make_candles(100)
        df = ohlcv_to_df(candles)
        result = full_analysis(df)
        self.assertIn(result["signal"], ("STRONG_BUY", "BUY", "NEUTRAL", "SELL", "STRONG_SELL"))
        self.assertIn("rsi", result)
        self.assertIn("reasons", result)
        self.assertIsInstance(result["reasons"], list)

    def test_individual_indicators(self):
        from trading.analysis import ohlcv_to_df, calc_rsi, calc_macd, calc_bollinger
        candles = self._make_candles(100)
        df = ohlcv_to_df(candles)

        rsi = calc_rsi(df)
        self.assertEqual(len(rsi), 100)

        macd = calc_macd(df)
        self.assertIn("macd", macd)
        self.assertIn("signal", macd)

        bb = calc_bollinger(df)
        self.assertIn("upper", bb)
        self.assertIn("lower", bb)


class TestAlerts(unittest.TestCase):
    """Test alert manager."""

    def test_add_and_list(self):
        from trading.alerts import AlertManager, Alert, AlertType
        mgr = AlertManager()
        alert = Alert(
            id="test-1", symbol="BTC/USDT",
            alert_type=AlertType.PRICE_ABOVE, threshold=100000.0,
        )
        mgr.add_alert(alert)
        self.assertEqual(len(mgr.list_alerts()), 1)

    def test_remove_alert(self):
        from trading.alerts import AlertManager, Alert, AlertType
        mgr = AlertManager()
        alert = Alert(
            id="test-2", symbol="ETH/USDT",
            alert_type=AlertType.PRICE_BELOW, threshold=1500.0,
        )
        mgr.add_alert(alert)
        self.assertTrue(mgr.remove_alert("test-2"))
        self.assertEqual(len(mgr.list_alerts()), 0)


class TestStrategies(unittest.TestCase):
    """Test strategy factory."""

    def test_get_strategy(self):
        from trading.strategies import get_strategy, DCAStrategy, MomentumStrategy
        dca = get_strategy("dca", amount_usd=100)
        self.assertIsInstance(dca, DCAStrategy)

        mom = get_strategy("momentum", position_usd=500)
        self.assertIsInstance(mom, MomentumStrategy)

    def test_unknown_strategy_raises(self):
        from trading.strategies import get_strategy
        with self.assertRaises(ValueError):
            get_strategy("does_not_exist")

    def test_dca_interval(self):
        from trading.strategies import DCAStrategy
        s = DCAStrategy(amount_usd=50, interval_seconds=86400)
        self.assertTrue(s.should_execute())  # never bought yet


class TestTradingTool(unittest.TestCase):
    """Test the agent tool interface."""

    def test_tool_schema(self):
        from nanobot.agent.tools.trading import TradingTool
        tool = TradingTool()
        self.assertEqual(tool.name, "trading")
        self.assertIn("action", tool.parameters["properties"])

    def test_strategies_action(self):
        import asyncio
        from nanobot.agent.tools.trading import TradingTool

        # Patch _ensure_client to avoid needing real API keys
        tool = TradingTool()
        tool._client = MagicMock()
        tool._alert_mgr = MagicMock()
        tool._portfolio_mon = MagicMock()

        result = asyncio.get_event_loop().run_until_complete(
            tool.execute(action="strategies")
        )
        self.assertIn("dca", result)
        self.assertIn("grid", result)


if __name__ == "__main__":
    unittest.main()
