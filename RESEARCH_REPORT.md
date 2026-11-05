# Research report: breakout_trend

Generated 2026-11-05 13:03 UTC. Long only, 4h candles, Alpaca data, 0.25% fee per side + 0.05% slippage. Results from 2021-01-01. Default settings: 20-candle breakout above SMA200, 2 ATR stop, trail 3 ATR, exit below EMA50.

## Summary

| Coin | Strategy CAGR | Buy-hold CAGR | 200-day filter CAGR | Strategy max DD | Buy-hold max DD | PF | Trades/yr | Luck p-value | Beats random entries |
|---|---|---|---|---|---|---|---|---|---|
| BTC/USD | +2.9% | +18.9% | +13.1% | 45% | 77% | 1.15 | 24 | 0.27 | 90% of random runs |

How to read: luck p-value under 0.05 is good evidence, over 0.2 means it could easily be chance. 'Beats random entries' should be 90%+ for the entry rule to be adding anything.

## BTC/USD

- No evidence it beats luck: chance gives a result this good 27% of the time.
- Loses to buy-and-hold on yearly return, and loses to the simple 200-day-average filter.
- Smaller worst drop than buy-and-hold (45% vs 77%), while in the market 25% of the time.
- 5% of the 144 nearby settings reach PF 1.2 (fragile: results depend on the exact settings).
- Best settings picked on 2021-2023 (PF 2.09) scored PF 0.69 on 2024 onward; the default scored 0.76. Picking the best past settings did not help.

| Year | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 |
|---|---|---|---|---|---|---|
| Strategy | +48.4% (19) | -10.9% (18) | +35.4% (25) | -8.1% (30) | -16.4% (27) | -14.1% (22) |
| Buy-hold | +57.9% | -64.2% | +155.9% | +121.0% | -6.3% | -8.2% |

Average trade -0.51% to +1.09% (90% range). Win rate 33%, in the market 25% of the time.

Profit factor by breakout length and trail (stop 2 ATR, exit EMA50):

| lookback \ trail_atr | 2.0 | 3.0 | 4.0 | 5.0 |
|---|---|---|---|---|
| 10 | 0.73 | 1.00 | 0.94 | 0.93 |
| 20 | 0.76 | 1.15 | 1.12 | 1.10 |
| 30 | 0.69 | 1.06 | 1.05 | 1.04 |
| 55 | 0.71 | 1.11 | 1.16 | 1.12 |

Profit factor by exit EMA and initial stop (breakout 20, trail 3 ATR):

| exit_ema \ stop_atr | 1.5 | 2.0 | 3.0 |
|---|---|---|---|
| 20 | 0.93 | 0.98 | 0.93 |
| 50 | 1.11 | 1.15 | 1.14 |
| 100 | 1.05 | 1.11 | 1.07 |

