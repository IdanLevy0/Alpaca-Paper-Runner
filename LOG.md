# LOG: Alpaca Paper Runner

Automated paper trading of BTC/USD on Alpaca from GitHub Actions, built from the DaviddTech-video research loop
(TradingView Backtests folder). Separate from the ESHA bot in Alpaca-Trading-Bot.

## 2026-11-03
- Read the research loop's results (TradingView Backtests/strategies_log.md): ~40 strategies on Bybit BTCUSDT.P 1h,
  long and short, 0.05% fees. None held up across 2021-2025; best 2026-only results (#15, #31, #35, #36) failed other years.
- Decisions with Idan: cloud runs (PC can be off), not a once-a-week strategy (4h to daily is fine), new folder.
- Idan pushed back on hourly checks. Agreed for exits: stop sits on Alpaca as a stop-limit and fires on its own;
  target and time exit now checked every 5 minutes. Entries stay once per closed 4h candle, since the rules are
  defined on candle closes and the backtest counts only those.
- Built: runner/strategies.py (3 long-only 4h candidates: trend_pullback, donchian_breakout, thrust_long, shared by
  backtest and runner), backtest/engine.py + run_backtest.py (yearly windows 2021-2026, 0.25% fee + 0.05% slippage,
  pass gate fixed before results), runner/run.py (paper guard, dry mode unless TRADING_ENABLED=true, state/KILL switch,
  daily entry cap, state committed to the repo), two GitHub workflows (paper-runner every 5 min, backtest by hand).
- Tests: 9 pass, including a parity test replaying candles through the live runner against the engine
  (112 trades: 49 stop, 36 target, 27 time; same entries, exits and reasons).
- NOT DONE: real-data backtest. Neither Claude's cloud workspace nor the sandbox on Idan's PC can reach Alpaca, so it
  runs from the GitHub backtest workflow (or locally). Strategy choice waits on that result.
- Known live vs backtest differences: target exits sell at market after a touch (backtest assumes the exact target);
  stop-limit has a 1% cushion and may not fill in a crash gap; GitHub can delay scheduled runs by minutes.
- Wrote SETUP.md and RESEARCH_LOOP_PROMPT.md (new long-only, Alpaca-fee loop prompt).
- Idan: reuse the existing paper account (ESHA bot keys), ESHA bot scrapped. No old GitHub repo exists; Idan creates an empty repo, Claude pushes, Idan adds the secrets himself.
- Local git repo created (branch main, first commit 0ee9b39). Waiting on Idan: empty public GitHub repo alpaca-paper-runner, secrets, then the backtest workflow.
