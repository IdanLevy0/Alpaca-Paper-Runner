# Research tools

## Run it
GitHub > Actions > **research** > Run workflow (about 5 minutes). Then `git pull` on your PC.

## What you get
- **RESEARCH_REPORT.md**: for BTC, ETH and SOL, the four questions below, in tables plus plain-English verdicts.
- **research/out/replay.html**: double-click to open in your browser. Pick a coin, step through every trade with
  Prev / Next, see why it bought and why it sold, the stop line under each trade, and growth of $1 against
  buy-and-hold and the 200-day-average filter.

## The four questions
1. **Is it luck?** *Luck p-value*: how often pure chance gives a result this good (bootstrap of the trade returns).
   Under 0.05 = real evidence; over 0.2 = easily chance. *Beats random entries*: same number of trades and holding
   times, entered at random candles, 500 times. The real rule should beat 90%+ of those.
2. **Does it beat simple?** Compared with buy-and-hold and with "hold only while above the 200-day average".
3. **Is it robust?** 144 nearby settings (breakout length, stop, trail, exit EMA). Heat tables show profit factor.
   A broad patch of good numbers = robust. One lucky cell = overfit.
4. **Does it generalize?** Best settings chosen on 2021-2023 are scored on 2024 onward (data they never saw),
   and the same rules run on three coins.

## Files
- research/fast.py: fast simulator (indicators computed once). tests/test_research.py proves it makes the same
  trades as the slow engine the live bot shares.
- research/stats.py: bootstrap, random-entry test, equity stats.
- research/run_research.py: grid, benchmarks, report, replay page. Settings at the top (coins, grid, dates).
