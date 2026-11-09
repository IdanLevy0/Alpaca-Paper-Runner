# Multi-day research protocol (written 2026-11-09, before any result)

Same spirit as stocks/PROTOCOL.md. Changing a rule after seeing results means a new card, not an edit.

## Data
- Daily bars from Alpaca (daily/download.py): the 100 stocks, 23 ETFs (sip feed, split- and dividend-adjusted)
  and BTC/USD. Survivorship bias: the 100 stocks are today's large caps; benchmarks share that bias.
- Stocks/ETFs: train 2016-04-01..2021-12-31, validation 2022-2023. BTC: train from first data..2022-12-31,
  validation 2023. Holdout 2024-01-01 on: SEALED for every card (run once, frozen rule, Idan's go-ahead).

## Execution model (daily/engine.py)
- Decide at the close of day t using only prices through t (plus the published trading calendar).
- Fill at the open of day t+1. Hold open-to-open. Long only, no leverage, unused money in cash at 0%.
- Positions drift with prices; costs are paid on every dollar traded: stocks/ETFs 0.03% per side
  (0% and 0.05% also shown), BTC 0.25% per side (Alpaca's fee; 0% and 0.40% shown).

## Gates
Best variant on train = highest Sharpe after base costs (the goal is steady returns, not the biggest number).
1. Train: mean daily return > 0 with day-bootstrap p < 0.05, AND Sharpe >= the card's benchmark Sharpe, AND
   Sharpe beats >= 90% of 200 random runs. Random runs: timing cards rotate the strategy's own in/out path by a
   random number of days (same time invested, same number of switches); selection cards pick random names from the
   same eligible pool on the same rebalance days.
2. Validation: mean daily return > 0 after costs AND Sharpe >= benchmark Sharpe - 0.25.
3. Holdout: once, for a card that passed 1 and 2, with Idan's go-ahead.

## Confidence and budget (used by the multi-strategy runner)
- Passed gates 1-3: up to 25% of the account. Passed 1-2: 10-15%. Everything else that Idan wants running: a 5%
  "learning" slice. Each slice is then scaled down (never up) so its expected volatility is <= 10% a year.
