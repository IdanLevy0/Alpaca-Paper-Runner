# H002: Late-day momentum (single stocks)
Status: REVIEWED (FAIL)
Market: stocks (100 large caps)      Holding: 25 minutes (15:30 to 15:55)
Pre-registered in stocks/PROTOCOL.md (commit 097cb24) before any result.

## Idea
The return from yesterday's close to 10:00 predicts the direction of the last half hour (hedging and rebalancing
flows at the close). Buy the biggest early gainers at 15:30, sell at 15:55.

## Sources
- Gao, Han, Li & Zhou (2018), "Market Intraday Momentum" (studied the S&P 500 ETF, SPY).
- Baltussen, Da, Lammers & Martens (2021), hedging demand and intraday momentum.

## Rules
See stocks/PROTOCOL.md H2. K in {5, 10}, market filter on/off.

## Results (train, 0.03%/side)
All four variants negative before costs (-0.6 to -1.3bp/day) and after (-4.1 to -7.2bp/day). Best latemom_k5_mkt
-4.05bp/day; validation -6.39bp/day.

## Skeptic review (written by Claude in the setup chat)
FAIL. Note the mismatch with the source: the papers test the index (SPY), not single stocks. A card testing SPY
itself (needs ETF data) is a fair, separate hypothesis.
