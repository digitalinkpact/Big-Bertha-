"""Technical analysis helpers using the `ta` library.

Provides RSI, MACD, Bollinger Bands, volume analysis, and composite signals.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
import ta


def ohlcv_to_df(candles: list[list]) -> pd.DataFrame:
    """Convert ccxt OHLCV list to a pandas DataFrame."""
    df = pd.DataFrame(candles, columns=["timestamp", "open", "high", "low", "close", "volume"])
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True)
    df.set_index("timestamp", inplace=True)
    return df


# ------------------------------------------------------------------
# Individual indicators
# ------------------------------------------------------------------

def calc_rsi(df: pd.DataFrame, window: int = 14) -> pd.Series:
    return ta.momentum.RSIIndicator(close=df["close"], window=window).rsi()


def calc_macd(df: pd.DataFrame) -> dict[str, pd.Series]:
    macd = ta.trend.MACD(close=df["close"])
    return {
        "macd": macd.macd(),
        "signal": macd.macd_signal(),
        "histogram": macd.macd_diff(),
    }


def calc_bollinger(df: pd.DataFrame, window: int = 20, std: float = 2.0) -> dict[str, pd.Series]:
    bb = ta.volatility.BollingerBands(close=df["close"], window=window, window_dev=std)
    return {
        "upper": bb.bollinger_hband(),
        "middle": bb.bollinger_mavg(),
        "lower": bb.bollinger_lband(),
        "pct_b": bb.bollinger_pband(),
    }


def calc_ema(df: pd.DataFrame, window: int = 20) -> pd.Series:
    return ta.trend.EMAIndicator(close=df["close"], window=window).ema_indicator()


def calc_atr(df: pd.DataFrame, window: int = 14) -> pd.Series:
    return ta.volatility.AverageTrueRange(
        high=df["high"], low=df["low"], close=df["close"], window=window
    ).average_true_range()


def calc_obv(df: pd.DataFrame) -> pd.Series:
    return ta.volume.OnBalanceVolumeIndicator(close=df["close"], volume=df["volume"]).on_balance_volume()


# ------------------------------------------------------------------
# Composite analysis
# ------------------------------------------------------------------

def full_analysis(df: pd.DataFrame) -> dict[str, Any]:
    """Run all indicators and return a summary dict."""
    rsi = calc_rsi(df)
    macd = calc_macd(df)
    bb = calc_bollinger(df)
    ema_20 = calc_ema(df, 20)
    ema_50 = calc_ema(df, 50)
    atr = calc_atr(df)
    obv = calc_obv(df)

    latest = df.iloc[-1]
    latest_rsi = rsi.iloc[-1]
    latest_macd_hist = macd["histogram"].iloc[-1]
    latest_bb_pct = bb["pct_b"].iloc[-1]

    # Simple signal scoring
    score = 0
    reasons: list[str] = []

    # RSI
    if latest_rsi < 30:
        score += 2
        reasons.append(f"RSI oversold ({latest_rsi:.1f})")
    elif latest_rsi < 40:
        score += 1
        reasons.append(f"RSI approaching oversold ({latest_rsi:.1f})")
    elif latest_rsi > 70:
        score -= 2
        reasons.append(f"RSI overbought ({latest_rsi:.1f})")
    elif latest_rsi > 60:
        score -= 1
        reasons.append(f"RSI approaching overbought ({latest_rsi:.1f})")

    # MACD
    if latest_macd_hist > 0:
        score += 1
        reasons.append("MACD histogram positive (bullish)")
    else:
        score -= 1
        reasons.append("MACD histogram negative (bearish)")

    # Bollinger %B
    if latest_bb_pct < 0.0:
        score += 2
        reasons.append("Price below lower Bollinger Band")
    elif latest_bb_pct < 0.2:
        score += 1
        reasons.append("Price near lower Bollinger Band")
    elif latest_bb_pct > 1.0:
        score -= 2
        reasons.append("Price above upper Bollinger Band")
    elif latest_bb_pct > 0.8:
        score -= 1
        reasons.append("Price near upper Bollinger Band")

    # EMA crossover
    if ema_20.iloc[-1] > ema_50.iloc[-1]:
        score += 1
        reasons.append("EMA20 > EMA50 (bullish trend)")
    else:
        score -= 1
        reasons.append("EMA20 < EMA50 (bearish trend)")

    # Overall signal
    if score >= 3:
        signal = "STRONG_BUY"
    elif score >= 1:
        signal = "BUY"
    elif score <= -3:
        signal = "STRONG_SELL"
    elif score <= -1:
        signal = "SELL"
    else:
        signal = "NEUTRAL"

    return {
        "price": float(latest["close"]),
        "rsi": float(latest_rsi),
        "macd_histogram": float(latest_macd_hist),
        "bollinger_pct_b": float(latest_bb_pct),
        "ema_20": float(ema_20.iloc[-1]),
        "ema_50": float(ema_50.iloc[-1]),
        "atr": float(atr.iloc[-1]),
        "obv": float(obv.iloc[-1]),
        "volume_24h": float(latest["volume"]),
        "signal": signal,
        "score": score,
        "reasons": reasons,
    }
