# B002: BTC multi-lookback momentum
Status: REVIEWED: FAIL (frozen 2026-11-09, tested 2026-11-11)   Market: BTC/USD   Holding: days to months
## Idea
From the library: "S12 Multi-Lookback TSMOM 1D" (Pine locked; our rules). Vote across 20/60/120-day returns.
## Rules: hold when at least `need` of the 3 returns are positive. Vol-scaled variant: size = min(1, 40% / 30-day vol).
## Variants: need in {2, 3} x scaled in {no, yes}
## Benchmark: BTC buy and hold. Random: rotated in/out path.
## Why it might fail: same as B001; vol scaling lowers return in strong rallies.

## Results (2026-11-11) -> research/results/B002.md
Best btc_tsmom3of3: -3%/yr train, beats 54% of random.
