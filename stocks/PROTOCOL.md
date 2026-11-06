# Stock intraday research protocol (written before any result)

Committed before any backtest of these hypotheses was run. Changing a rule after seeing results means
starting a new, separately logged hypothesis, not editing this one.

## Data and periods
- 100 liquid US stocks (Day-Trading-Lab top-100 universe), Alpaca sip 5-minute bars, split-adjusted,
  regular session, cleaning rules from the lab (stocks/data.py). Survivorship bias: stocks listed today only.
- Train 2016-04-01 to 2021-12-31. Validation 2022-01-01 to 2023-12-31.
  Holdout 2024-01-01 to 2026-10-27: SEALED. Run once, only for a frozen rule, only with Idan's go-ahead.

## Common execution rules
- Long only. Decisions at 5-minute bar closes. Entry at the next bar's open.
- Flat by the close: every position exits no later than the open of the 15:55 bar.
- Up to K positions at once, each 1/K of equity; unused slots sit in cash. Equity compounds daily.
- Costs per side: 0.03% (base: $0 commission + half spread + slippage on large caps).
  Sensitivity also reported at 0% and 0.05%.
- Stops are checked on 5-minute lows; a bar that opens below the stop exits at its open.
- Only valid sessions; a stock needs 20 prior valid sessions for its volatility statistics.

## H1: Intraday reversal after an unusually sharp drop
Source: short-horizon reversal / liquidity-provision literature (e.g. Heston, Korajczyk & Sadka 2010 on
intraday return patterns; Nagel 2012 "Evaporating Liquidity" on reversal as liquidity provision).
- Decision times: 10:30, 11:30, 12:30, 13:30, 14:30 (closes of slots 11, 23, 35, 47, 59).
- sigma60: root-mean-square of the stock's 60-minute block returns over the prior 20 valid sessions
  (6 blocks a day: 09:30-10:30, ..., 14:30-15:30).
- z = (last 60-minute return) / sigma60. Buy the most negative z first, only if z <= -Z, not already held.
- Exit after H bars or at 15:55, whichever first. Stop at entry x (1 - 2 x sigma60).
- K = 5. Variants: Z in {2, 3} x H in {12 bars (1h), 24 bars (2h)} = 4 variants.

## H2: Late-day momentum
Source: Gao, Han, Li & Zhou (2018) "Market Intraday Momentum" (first half-hour return predicts the last
half-hour); Baltussen, Da, Lammers & Martens (2021) on hedging demand driving it.
- Signal s = close of the 10:00 bar end (slot 5 close) / previous valid session close - 1.
- Decision at 15:30 (slot 71 close). Buy the K stocks with the largest s, only if s > 0. Exit at 15:55 open.
- Variants: K in {5, 10} x market filter in {off, on (only trade when the universe-average s > 0)} = 4.

## H3: Overnight vs intraday (descriptive, not a strategy)
Equal-weight universe return split into overnight (prev close to open) and intraday (open to close),
per year. Shows how much of the market's return a flat-by-close trader can ever reach.

## Gates
1. Train: pick the variant with the best mean daily return after base costs.
   It must have: mean daily return > 0 with day-bootstrap p < 0.05, and beat the random baseline
   (same decision times, same number of picks, random eligible stocks, same exits) at >= 90th percentile.
2. Validation: the same frozen variant must have mean daily return > 0 after base costs.
3. Holdout: one run, only after Idan agrees, for a variant that passed 1 and 2.
A hypothesis that fails a gate stops there and is logged. Paper trading a failed hypothesis is allowed
only as a clearly labelled learning bot.
