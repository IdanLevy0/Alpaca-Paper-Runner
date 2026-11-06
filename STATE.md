# State (keep under 25 lines)
- Live: BTC paper bot (breakout_trend, 4h) on GitHub every 5 min via cron-job.org. Flat, no trades yet.
- Research team set up 2026-11-06 (Agent HQ). Agents: lead, researcher, quant, skeptic, risk, reporter.
- Stocks: 100 large caps, 5-min bars 2016-2026 cached. Engine + tests ready (`py -m pytest -q`).
- Tested: H001 intraday reversal FAIL (small edge < costs), H002 late-day momentum FAIL.
- Holdout 2024+ untouched for all stock cards.
- Not yet: ETF data (SPY, QQQ...), stock paper bot, stock replay viewer.
## Next 3
1. Researcher: 2 new DRAFT cards that fit (long only, intraday, existing data). Candidates to consider:
   reversal with limit-order entry; opening gap behaviour; volume-spike continuation.
2. Quant: freeze + test the strongest draft.
3. Skeptic review, then reporter digest.
