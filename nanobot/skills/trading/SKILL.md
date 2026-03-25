---
name: trading
description: Binance.US trading — market analysis, automated orders, portfolio tracking, alerts. Requires API keys.
metadata: {"nanobot":{"emoji":"📈","requires":{"env":["BINANCE_US_API_KEY","BINANCE_US_API_SECRET"],"pip":["ccxt","ta","pandas","numpy"]}}}
---

# Binance.US Trading Skill

## Quick Start

Ensure your environment has the API keys set:
```bash
export BINANCE_US_API_KEY="your_key"
export BINANCE_US_API_SECRET="your_secret"
```

## Available Actions (via `trading` tool)

| Action | Description | Required Params |
|--------|-------------|-----------------|
| `ticker` | Current price/bid/ask/volume | `symbol` |
| `analyze` | Full technical analysis (RSI, MACD, Bollinger, EMA) | `symbol`, `timeframe` |
| `balance` | Account balances | — |
| `buy` | Place buy order | `symbol`, `amount`, `price` (limit) or `order_type=market` |
| `sell` | Place sell order | `symbol`, `amount`, `price` (limit) or `order_type=market` |
| `cancel_order` | Cancel open order | `symbol`, `order_id` |
| `open_orders` | List open orders | `symbol` |
| `portfolio` | Portfolio snapshot + P&L | — |
| `add_alert` | Create price/volume alert | `symbol`, `alert_type`, `threshold` |
| `list_alerts` | Show all alerts | — |
| `check_alerts` | Evaluate alerts against live prices | — |
| `strategies` | List available trading strategies | — |

## Strategy Examples

### Dollar-Cost Averaging (DCA)
Buy $50 of BTC every day regardless of price:
```
Use the trading tool: action=analyze, symbol=BTC/USDT, timeframe=1d
Then: action=buy, symbol=BTC/USDT, amount=<calculated>, order_type=market
```

### Momentum / Swing
Analyze technicals and trade when signals align:
```
action=analyze, symbol=BTC/USDT, timeframe=1h
```
The analysis returns a signal: STRONG_BUY, BUY, NEUTRAL, SELL, STRONG_SELL with a confidence score and reasons.

### Grid Trading
Place buy orders below current price and sell orders above:
```
action=ticker, symbol=ETH/USDT   (get current price)
action=buy, symbol=ETH/USDT, amount=0.1, price=<grid_level>
action=sell, symbol=ETH/USDT, amount=0.1, price=<grid_level>
```

## Alerts

Set price alerts:
```
action=add_alert, symbol=BTC/USDT, alert_type=price_above, threshold=100000
action=add_alert, symbol=ETH/USDT, alert_type=price_below, threshold=2000
action=add_alert, symbol=BTC/USDT, alert_type=volume_spike, threshold=500000000
```

## Security

- API keys are read from environment variables — **never** hardcoded
- Daily trading limit enforced (default $1,000, configurable via `TRADING_DAILY_LIMIT`)
- Stop-loss / take-profit defaults: 5% / 10%
- All orders are logged via `loguru`
- **Never enable withdrawal permissions** on your API key
- Use IP whitelisting on Binance.US when possible
- Rotate keys every 3–6 months

## Binance.US Notes

- API base: `https://api.binance.us` (different from global Binance)
- Limited asset selection vs global Binance
- Subject to US regulatory restrictions
- Different rate limits than global Binance
