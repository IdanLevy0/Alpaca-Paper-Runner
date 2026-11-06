# Setup: Alpaca paper runner on GitHub Actions

Runs in the cloud every 5 minutes, so your PC can be off. Paper only: there is no live trading URL in the code.

## 1. Paper account
Uses the existing paper account (keys are in ../Alpaca-Trading-Bot/.env). The ESHA bot is scrapped; remove its
scheduled task with `.\scripts\register_bot_task.ps1 -Remove` from that folder.

## 2. Make the GitHub repo
1. On github.com, create a new repo named `alpaca-paper-runner` (public = free every-5-minute runs;
   private = change `*/5` to `*/30` in `.github/workflows/paper-runner.yml` to stay inside the free 2,000 minutes).
2. In PowerShell, from this folder:
   ```
   git init -b main
   git add .
   git commit -m "paper runner v1"
   git remote add origin https://github.com/IdanLevy0/alpaca-paper-runner.git
   git push -u origin main
   ```
3. Repo Settings > Secrets and variables > Actions:
   - Secrets: `ALPACA_API_KEY`, `ALPACA_SECRET_KEY` (the paper keys from step 1)
   - Variables: `TRADING_ENABLED` = `false` for now

## 3. Run the real-data backtest
Actions tab > backtest > Run workflow. It runs the tests, downloads BTC/USD 4h history from Alpaca,
and commits BACKTEST_RESULT.md. (Or locally: `py -3.12 -m backtest.run_backtest --refresh`.)
Pick the strategy that passes the gate and set `STRATEGY` in `runner/config.py`.
If none passes, keep the runner in dry mode while the research loop finds one.

## 4. Dry run, then paper
- With `TRADING_ENABLED=false` the runner makes every decision and logs it to `state/runs.log`, but sends no orders.
- After a day of clean dry runs, set `TRADING_ENABLED` to `true`. Orders start on the next pass.

## Stopping it
- Fastest: set the `TRADING_ENABLED` variable to `false` (works from the GitHub mobile app).
- Or add an empty file `state/KILL` to the repo.
- Or Actions > paper-runner > ... > Disable workflow.
An open position keeps its stop order on Alpaca even when the runner is off.

## What gets saved
`state/state.json` (open trade), `state/trades.csv` (closed trades), `state/runs.log` (last 500 passes).

## Stock paper bot (stockbot/)
Runs in the same GitHub workflow as the BTC bot (every 5 minutes, cron-job.org), only during market hours.
- Strategy: stockbot/config.py (now H001 reversal_z3_h24 as a LEARNING BOT; it failed the research gate).
- Budget: 50% of paper equity, up to 5 positions (10% each), whole shares, stop order on Alpaca for each,
  time exit after 2 hours, everything sold from 15:55, no trading on early-close days, daily loss stop -2%.
- Order ids start with `stk-`. It never reads or sells BTC/USD.
- Switch on: GitHub > Settings > Secrets and variables > Actions > Variables > New: `STOCKS_ENABLED` = `true`.
  Without it (or with `false`) the bot runs in DRY mode: same decisions, logged, no orders.
- Logs: state/stocks/runs.log (every pass), trades.csv (every trade), days.csv (one line per day).
- Real-data check without orders: Actions > stockbot-check > Run workflow -> state/stocks/check.md.
- Stop: set `STOCKS_ENABLED` to `false`, or add state/KILL (stops BOTH bots' orders).
