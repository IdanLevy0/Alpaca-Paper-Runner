# Hypothesis index
Check this before proposing anything. Newest at the bottom. "Before costs / after costs" are per the card's base cost.

## Stocks, intraday (100 large caps, 5-min bars, flat by close, 0.03%/side)
| Card | Idea | Status | Result |
|---|---|---|---|
| [H001](H001-intraday-reversal.md) | Buy unusually sharp 60-min drops (z <= -2/-3), hold 1-2h | REVIEWED: FAIL | Best +1.1bp/day before costs, -3.0bp/day after (-7%/yr); entries beat 94% of random picks, but costs (~4bp/day) eat it. Valid 2022-23 -2.6bp/day |
| [H002](H002-late-day-momentum.md) | Buy biggest yesterday-close-to-10:00 gainers at 15:30, sell 15:55 | REVIEWED: FAIL | Negative even before costs (-0.6bp/day); after costs -4.1bp/day. The source studied the S&P 500 index, not single stocks |
| H003 (not a card) | Overnight vs intraday split | Descriptive | 2016-2023 most of the 100 stocks' return came overnight (e.g. 2021 +20.9% overnight vs +4.5% intraday) |
| [H004](H004-high-volume-gap-and-go.md) | Buy stocks gapping up >=1-2% on 2-3x opening volume when they break the first-30-min high; stop at range low, exit 15:55 | REVIEWED: FAIL | Best (gap 2%, 3x vol) +0.33bp/day after costs, +11.7bp/trade, but only ~25 trades/yr: p 0.18. Valid 2022-23 +1.2bp/day. Follow-up: same frozen rule on new stocks |
| [H005](H005-volume-spike-continuation.md) | Buy a 5-min bar with 4-8x normal volume that closes in its top quarter; hold 30-60 min | REVIEWED: FAIL | Under +1bp/day before costs; -1.5 to -10bp/day after (fires up to 9x/day). Valid -2.3bp/day |

## Multi-day (daily bars, fills next open; daily/PROTOCOL.md)
| Card | Idea | Status | Result |
|---|---|---|---|
| [E001](E001-etf-trend.md) | 5 asset-class ETFs, each held only while above its trend | FROZEN | Running |
| [E002](E002-low-volatility-stocks.md) | Hold the calmest 10-20 of the 100 stocks, monthly | FROZEN | Running |
| [E003](E003-weekly-reversal.md) | Buy last week's biggest losers, hold a week | FROZEN | Running |
| [E004](E004-turn-of-month.md) | SPY only around the turn of the month | FROZEN | Running |
| [B001](B001-btc-trend.md) | BTC only above its N-day average | FROZEN | Running |
| [B002](B002-btc-momentum.md) | BTC when 20/60/120-day momentum votes yes | FROZEN | Running |
| [B003](B003-btc-turn-of-month.md) | BTC around the turn of the month | FROZEN | Running |

## Crypto (Alpaca BTC/USD, 0.25%/side, long only), for reference
| Card | Idea | Result |
|---|---|---|
| C001 | 42 TradingKit ideas on Bybit BTCUSDT.P 1h (see ../TradingView Backtests/strategies_log.md) | None held up across 2021-2025 |
| C002 | trend_pullback 4h (RSI2 < 10 above EMA200) | PF 0.92, 2/6 years up |
| C003 | donchian_breakout 4h (20-bar high, fixed 4 ATR target) | PF 0.76 |
| C004 | thrust_long 4h (range expansion) | PF 0.61 |
| C005 | breakout_trend 4h (S38/S62 rebuild, trailing stop, EMA50 exit), live on paper | PF 1.15 BTC; luck p 0.27; 5% of 144 settings reach PF 1.2; best 2021-23 settings PF 2.09 -> 0.69 on 2024+ |
