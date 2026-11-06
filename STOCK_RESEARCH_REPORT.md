# Stock intraday research: train + validation

Rules: stocks/PROTOCOL.md (committed before any result). 100 stocks, 5-minute bars, long only, flat by 15:55. Base cost 0.03% per side. Train 2016-04 to 2021-12, validation 2022-2023. Holdout (2024 on) sealed.

## All variants on train

| Variant | Mean/day (0% cost) | Mean/day (0.03%) | Mean/day (0.05%) | Per year (0.03%) | Sharpe | Max DD | Trades/day | Avg trade | Win |
|---|---|---|---|---|---|---|---|---|---|
| reversal_z2_h12 | +1.58bp | -6.41bp | -11.74bp | -14.9% | -1.84 | 62% | 6.7 | -4.8bp | 46% |
| reversal_z2_h24 | +2.19bp | -5.25bp | -10.21bp | -12.4% | -1.24 | 58% | 6.2 | -4.2bp | 47% |
| reversal_z3_h12 | +0.78bp | -3.35bp | -6.10bp | -8.1% | -1.32 | 39% | 3.4 | -4.9bp | 47% |
| reversal_z3_h24 (best) | +1.11bp | -2.96bp | -5.67bp | -7.2% | -0.91 | 39% | 3.4 | -4.4bp | 45% |
| latemom_k5 | -1.29bp | -7.22bp | -11.18bp | -16.6% | -2.99 | 65% | 4.9 | -7.3bp | 38% |
| latemom_k5_mkt (best) | -0.60bp | -4.05bp | -6.35bp | -9.7% | -2.09 | 45% | 2.9 | -7.0bp | 37% |
| latemom_k10 | -1.28bp | -7.16bp | -11.07bp | -16.5% | -3.59 | 65% | 9.8 | -7.3bp | 37% |
| latemom_k10_mkt | -0.81bp | -4.26bp | -6.56bp | -10.2% | -2.78 | 46% | 5.8 | -7.4bp | 36% |

bp = basis points (1bp = 0.01%). Mean/day is the whole portfolio's average daily return.

## Gate check: reversal_z3_h24

- Train after costs: -2.96bp/day (-7.2%/yr), luck p-value 0.989, beats 94% of random-stock runs.
- Gate 1 (train): FAIL.
- Validation 2022-2023: -2.56bp/day (-6.2%/yr), 3.0 trades/day.
- Gate 2 (validation): not reached.

| Year | 2016 | 2017 | 2018 | 2019 | 2020 | 2021 | 2022 | 2023 |
|---|---|---|---|---|---|---|---|---|
| Return | -8.1% | -10.3% | -10.8% | -10.2% | +5.6% | -8.0% | -7.4% | -5.6% |

## Gate check: latemom_k5_mkt

- Train after costs: -4.05bp/day (-9.7%/yr), luck p-value 1.000, beats 72% of random-stock runs.
- Gate 1 (train): FAIL.
- Validation 2022-2023: -6.39bp/day (-14.9%/yr), 2.6 trades/day.
- Gate 2 (validation): not reached.

| Year | 2016 | 2017 | 2018 | 2019 | 2020 | 2021 | 2022 | 2023 |
|---|---|---|---|---|---|---|---|---|
| Return | -3.6% | -8.7% | -14.1% | -13.4% | -0.0% | -15.2% | -14.7% | -14.8% |

## H3: where the market's return happens (equal-weight 100 stocks, 2016-2023)

| Year | Overnight (close to open) | Intraday (open to close) |
|---|---|---|
| 2016 | +3.1% | +6.7% |
| 2017 | +15.0% | +5.2% |
| 2018 | +9.5% | -15.6% |
| 2019 | +14.9% | +10.5% |
| 2020 | +16.2% | -4.4% |
| 2021 | +20.9% | +4.5% |
| 2022 | -11.3% | +3.7% |
| 2023 | +2.5% | +13.5% |

A flat-by-close strategy can only ever earn from the intraday column.
