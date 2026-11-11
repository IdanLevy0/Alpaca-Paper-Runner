# E001: ETF trend filter (Faber-5)
Status: REVIEWED: FAIL (frozen 2026-11-09, tested 2026-11-11)   Market: ETFs   Holding: weeks to months
## Idea
Hold each of 5 asset-class ETFs (SPY, EFA, IEF, VNQ, DBC) at 1/5 while its trend is up, else keep that 1/5 in cash.
Aim: similar return to holding all five, with much smaller crashes.
## Sources
- Faber (2007), "A Quantitative Approach to Tactical Asset Allocation": 10-month average filter on 5 asset classes,
  1973-2005, similar return to buy-and-hold with far lower drawdowns.
- Moskowitz, Ooi, Pedersen (2012), "Time Series Momentum", JFE: 12-month own-return predicts the next month across 58 futures.
## Rules
Signal "sma200": close > average of the last 200 closes. Signal "ret12m": close / close 252 days ago - 1 > 0.
Check at the last close of each month ("month") or each week ("week"); fill next open.
## Variants: sma200/month, sma200/week, ret12m/month, ret12m/week
## Benchmark: the 5 ETFs equal weight, rebalanced monthly. Random: rotated in/out path.
## Why it might fail
Choppy markets cause whipsaws; 2016-2021 had few long bear markets, so the filter mostly costs return in train.
Code: daily/strategies.py TrendETF.

## Results (2026-11-11) -> research/results/E001.md
Best trend_sma200_month: +6.7%/yr, Sharpe 1.08 vs 0.94, drawdown 7% vs 26%, but beats only 79% of random timings (needs 90). Valid 2022-23 -1.8%/yr.
