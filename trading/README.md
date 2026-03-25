# Trading Systems

Algorithmic and crypto trading bots, market analysis tools, and backtesting simulators.

## Status: Planned

## Planned Components

- `crypto_trading_bot.py` — Crypto trading bot with exchange integration
- `backtester/` — Historical data backtesting engine
- `analyzers/` — Market analysis and signal generators
- `simulators/` — Paper trading simulators

## Dependencies (to add to pyproject.toml)

```
pandas>=2.0
numpy>=1.24
ccxt>=4.0          # Crypto exchange integration
ta>=0.11           # Technical analysis
websockets>=12.0   # Real-time data feeds
```

## Getting Started

1. Add API keys for your exchange(s) to `.env`
2. Install dependencies: `pip install pandas numpy ccxt ta`
3. Create your first strategy in this directory
