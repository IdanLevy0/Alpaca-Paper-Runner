# E002: Low-volatility stocks
Status: FROZEN (2026-11-09, before any result)   Market: the 100 stocks   Holding: 1 month
## Idea
Calm stocks have historically earned about as much as jumpy ones with much less risk. Hold the calmest N of the 100.
## Sources
- Baker, Bradley, Wurgler (2011), "Benchmarks as Limits to Arbitrage", FAJ: low-volatility US stocks beat high-volatility
  ones 1968-2008.  - Ang, Hodrick, Xing, Zhang (2006), JF: high idiosyncratic volatility stocks earn low returns.
- Frazzini, Pedersen (2014), "Betting Against Beta", JFE.
## Rules
At each month's last close: volatility = std of daily log returns over the last L days (needs L+1 closes).
Hold the N lowest, equal weight, until next month end.
## Variants: N in {10, 20} x L in {60, 250}
## Benchmark: all 100 equal weight monthly. Random: N random stocks from the same eligible pool each month.
## Why it might fail
In a strong bull market (2016-2021, tech-led) calm stocks lag; it may win on risk (Sharpe) but not on return.
Code: daily/strategies.py LowVol.
