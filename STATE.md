# State (keep under 25 lines)
- Live: BTC paper bot (breakout_trend, 4h) on GitHub every 5 min via cron-job.org. Flat, no trades yet.
- Research team set up 2026-11-06 (Agent HQ). Agents: lead, researcher, quant, skeptic, risk, reporter.
- Stocks: 100 large caps, 5-min bars 2016-2026 cached. Engine + tests ready (`py -m pytest -q`).
- Tested: H001 reversal FAIL, H002 late-day momentum FAIL, H004 gap-and-go FAIL (right direction, too few trades: p 0.18),
  H005 volume spike FAIL (no edge before costs). 4 stock cards tried, so luck risk is rising.
- Holdout 2024+ untouched for all stock cards.
- Stock paper bot built 2026-11-06 (stockbot/, H001 learning bot), first trading day Monday. Agents may not edit it.
- Not yet: ETF data (SPY, QQQ...). Stock replay page published 2026-11-06 (H001, Oct 9-Nov 6).
- Windows command setup fixed 2026-11-06; follow CLAUDE.md "Windows shell rules".
- Digest 2026-11-06 written. BTC bot flat.
- Multi-day research 2026-11-11 (daily/): E001-E004, B001-B003 tested. Only E002 low-vol passed train+valid; it FAILED
  the one-time holdout (Sharpe 0.89 vs 1.25). Nothing has passed every gate yet.
- Live paper since 2026-11-11 (learning bots, 5% each, vol-capped): H001 intraday (BUDGET_PCT 0.05), E001 ETF trend,
  E002 low-vol, B003 BTC turn-of-month (daily/config.py SLEEVES, needs DAILY_ENABLED=true). BTC bot ignores sleeve BTC.
## Next 3
1. Watch the first daily rebalances (state/daily/runs.log, trades.csv): fills vs decision prices.
2. Researcher: new multi-day cards only with a fresh idea + source; holdout for stocks is now used for E002 only.
3. Reporter digest of the multi-day results.
