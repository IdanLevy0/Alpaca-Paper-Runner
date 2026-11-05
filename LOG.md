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
- Real-data backtest (GitHub workflow, Alpaca BTC/USD 4h 2021 to 2026-11-03): all 3 fail the gate. trend_pullback PF 0.92 (2/6 years up, DD 58.5%), donchian_breakout PF 0.76 (0/6), thrust_long PF 0.61 (0/6). Fees ~18%/yr drag at ~30 trades/yr. Runner stays DRY with trend_pullback as a plumbing test; real candidates come from the research loop. Waiting on the text of the run's warning + notice.
- First runner pass failed: the pasted secret had a trailing newline (InvalidHeader). The error text contained the secret key and was committed to the public repo in state/runs.log (my bug). Fixed: keys stripped on load, errors redacted (header errors logged by type only), no traceback to the Actions log, 3 new tests (12 pass), log line scrubbed. Idan must regenerate the Alpaca paper keys; the old secret stays in git history, so regenerating is what makes it harmless.
- 2026-11-03 23:04Z: first green pass with regenerated keys. DRY, trend_pullback, read the 16:00Z 4h candle (correct latest closed bar), no signal, state committed. Scheduled every-5-min runs should follow. Next: Idan pulls tomorrow, Claude checks a day of runs.log; then optional TRADING_ENABLED=true plumbing test.
- Searched the Trader.dev library (TradingKit MCP; Pine locked on Free). Most top hits fail red flags (e.g. 1,630 trades on daily candles). Best family: S38/S62 (Donchian-20 breakout, trend gate, trend exits). Its 132 published trades (R2-09) re-scored with 0.6% Alpaca round-trip cost: PF 1.91, 5 of 7 years profitable (2022 and 2025 lose), avg move +2.2%/trade, ~20 trades/yr. Rebuilt as breakout_trend (close > prior 20-bar high and > SMA200, 2 ATR initial stop, stop trails 3 ATR below highest close, exit on close < EMA50). Runner + engine now support candle-close exit management (stop raised on Alpaca by cancel/replace). Parity test for it passes (35 trades, stop + signal exits). Backtest now covers BTC/USD and ETH/USD. 13 tests pass. Waiting on the real-data backtest run.
- Real-data backtest of breakout_trend FAILS the gate: BTC PF 1.15, 2/6 years up, DD 44.5%; ETH PF 1.08, 2/6. Does not reproduce the library's PF 1.91 (exact locked rules unknown; library result likely selection-flattered, R2-09 = round 2, variant 9). Idan had already set TRADING_ENABLED=true (PAPER mode since 23:21Z). Switched runner to breakout_trend as a labelled paper forward test (least-bad candidate, exercises trailing-stop plumbing), not a proven edge. Noticed scheduled runs are irregular (23:04, 23:21), not every 5 min yet.
- 2026-11-04: overnight only ONE scheduled run (02:42Z) between 23:21Z and 14:00Z: GitHub cron skipped ~3 candle checks. No trades (no signal on the checked candle). Runner now logs MISSED N candle(s). Fix: external cron (cron-job.org) triggering workflow_dispatch every 5 min with a fine-grained token (Actions: write, this repo only), set up by Idan.
- 2026-11-04 evening: no trades yet. Added a diagnostic to each new-candle log line (distance to 20-bar high, above/below SMA200) so 'no signal' can be told apart from a bug. 15 tests pass.
- 2026-11-05: Built research tools (#1 research workflow + #2 replay viewer). breakout_trend made configurable (make_breakout_trend; defaults unchanged, parity still passes). research/fast.py matches the engine trade for trade on 3 settings. Report: luck p-value (bootstrap), random-entry percentile, buy-hold + 200-day filter benchmarks, 144-setting grid with PF heat tables, 2021-23 in-sample vs 2024+ out-of-sample, BTC/ETH/SOL. replay.html (lightweight-charts 4.1.3): trade stepper with why-bought / why-sold, stop path, equity vs benchmarks; checked rendered (light, dark, phone) on synthetic data, fixed stop-line and scroll bugs. 20 tests pass. Real run = GitHub research workflow.
