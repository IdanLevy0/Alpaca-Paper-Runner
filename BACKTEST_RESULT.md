# Backtest result: BTC/USD 4h, long only, Alpaca data

Bars: 2021-01-01T04:00:00Z to 2026-11-03T16:00:00Z (12795 bars). Fee 0.25% per side + 0.05% slippage.
Gate: profitable in >= 4 of 6 years, PF >= 1.2, >= 25 trades per year on average.

| Strategy | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 | All PF | Trades/yr | Max DD | Gate |
|---|---|---|---|---|---|---|---|---|---|---|
| trend_pullback | +45.7% (30) | -27.1% (19) | +4.9% (43) | -11.2% (45) | -20.9% (26) | -16.6% (27) | 0.92 | 32 | 58.5% | fail |
| donchian_breakout | -3.2% (26) | -26.1% (21) | -16.8% (36) | -18.9% (38) | -7.5% (30) | -29.5% (25) | 0.76 | 29 | 76.7% | fail |
| thrust_long | -12.4% (23) | -13.9% (25) | -36.8% (45) | -34.0% (42) | -30.4% (32) | -31.2% (27) | 0.61 | 32 | 87.1% | fail |
| buy and hold | +57.9% | -64.2% | +155.9% | +121.0% | -6.3% | -11.4% | | | | |

Cells: return for trades entered that year (trade count).
