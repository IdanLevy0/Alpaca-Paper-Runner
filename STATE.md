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
## Next 3
1. Monday 2026-11-09: first live paper day of the stock bot. Compare real fills to the 0.03%/side cost assumption.
2. Researcher (only if Idan asks): card H006 = H004's frozen rule (gap 2%, 3x volume) on a wider stock universe it has never
   seen. Needs a data download first; do not retune G or R.
3. Reporter digest of H004/H005.
