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
| [E001](E001-etf-trend.md) | 5 asset-class ETFs, each held only while above its trend | REVIEWED: FAIL | Best trend_sma200_month: +6.7%/yr, Sharpe 1.08 vs 0.94, drawdown 7% vs 26%, but beats only 79% of random timings (needs 90). Valid 2022-23 -1.8%/yr. |
| [E002](E002-low-volatility-stocks.md) | Hold the calmest 10-20 of the 100 stocks, monthly | FAIL at holdout (passed train + validation) | Holdout 2024-26: +11.5%/yr, Sharpe 0.89 vs 1.25. Train: lowvol_n10_l60 +17.7%/yr, Sharpe 1.29 vs 0.98, vol 13% vs 18%, drawdown 23% vs 35%, beats 100% of random picks. Valid 2022-23 +7.2%/yr, Sharpe 0.63 vs 0.41. |
| [E003](E003-weekly-reversal.md) | Buy last week's biggest losers, hold a week | REVIEWED: FAIL | Best weekrev_n10_l10: Sharpe 0.66 vs 0.98, beats 28% of random picks, ~67x turnover, 58% drawdown. |
| [E004](E004-turn-of-month.md) | SPY only around the turn of the month | REVIEWED: FAIL | Best tom_m1_p4: +8.0%/yr, Sharpe 0.92 vs SPY 1.08 (in the market ~20% of days), 90% vs random. Valid -0.1%/yr. |
| [B001](B001-btc-trend.md) | BTC only above its N-day average | REVIEWED: FAIL | Best btc_sma100: -19%/yr on 2021-22 train (whipsaws at 0.25%/side), beats 41% of random. |
| [B002](B002-btc-momentum.md) | BTC when 20/60/120-day momentum votes yes | REVIEWED: FAIL | Best btc_tsmom3of3: -3%/yr train, beats 54% of random. |
| [B003](B003-btc-turn-of-month.md) | BTC around the turn of the month | REVIEWED: FAIL (close) | Best btc_tom_m4_p2: +26.8%/yr vs BTC -25%/yr on 2021-22, beats 98% of random, but p 0.076 on only 2 years of data. Valid 2023 +14.9% (BTC +155%). |

## Crypto (Alpaca BTC/USD, 0.25%/side, long only), for reference
| Card | Idea | Result |
|---|---|---|
| C001 | 42 TradingKit ideas on Bybit BTCUSDT.P 1h (see ../TradingView Backtests/strategies_log.md) | None held up across 2021-2025 |
| C002 | trend_pullback 4h (RSI2 < 10 above EMA200) | PF 0.92, 2/6 years up |
| C003 | donchian_breakout 4h (20-bar high, fixed 4 ATR target) | PF 0.76 |
| C004 | thrust_long 4h (range expansion) | PF 0.61 |
| C005 | breakout_trend 4h (S38/S62 rebuild, trailing stop, EMA50 exit), live on paper | PF 1.15 BTC; luck p 0.27; 5% of 144 settings reach PF 1.2; best 2021-23 settings PF 2.09 -> 0.69 on 2024+ |
