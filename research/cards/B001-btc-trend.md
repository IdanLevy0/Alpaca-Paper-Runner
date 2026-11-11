# B001: BTC trend filter
Status: REVIEWED: FAIL (frozen 2026-11-09, tested 2026-11-11)   Market: BTC/USD (Alpaca, 0.25%/side)   Holding: days to months
## Idea
Hold BTC only while it trades above its N-day average. Idea from the TradingKit (Trader.dev) library, "BTC FROZEN
BASELINE (no stop)" (SMA filter; Pine locked, so these exact rules are ours). Library result was on Bybit perpetual,
not Alpaca spot with 0.25% fees.
## Rules: daily close > mean of last N closes -> hold 100% of the slice, else cash. Checked daily.
## Variants: N in {20, 50, 100, 200}
## Benchmark: BTC buy and hold. Random: rotated in/out path.
## Why it might fail: short history on Alpaca (train ~2021-2022), whipsaw costs at 0.25%/side.

## Results (2026-11-11) -> research/results/B001.md
Best btc_sma100: -19%/yr on 2021-22 train (whipsaws at 0.25%/side), beats 41% of random.
