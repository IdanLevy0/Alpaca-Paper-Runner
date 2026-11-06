# State (keep under 25 lines)
- Live: BTC paper bot (breakout_trend, 4h) on GitHub every 5 min via cron-job.org. Flat, no trades yet.
- Research team set up 2026-11-06 (Agent HQ). Agents: lead, researcher, quant, skeptic, risk, reporter.
- Stocks: 100 large caps, 5-min bars 2016-2026 cached. Engine + tests ready (`py -m pytest -q`).
- Tested: H001 intraday reversal FAIL (small edge < costs), H002 late-day momentum FAIL.
- Holdout 2024+ untouched for all stock cards.
- Not yet: ETF data (SPY, QQQ...), stock paper bot, stock replay viewer.
- H004 (gap-and-go) and H005 (volume-spike continuation) drafted 2026-11-06, status DRAFT, not tested yet.
- Windows command setup fixed 2026-11-06; follow CLAUDE.md "Windows shell rules".
- Digest 2026-11-06 written. BTC bot flat.
## Next 3
1. Quant: write strategy code for H004/H005 in stocks/strategies.py, freeze (commit card + code), then test.
2. Skeptic review of tested cards; 4 cards tried so far, so luck risk is rising.
3. Reporter digest.
