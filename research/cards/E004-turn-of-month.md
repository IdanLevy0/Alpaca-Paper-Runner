# E004: Turn of the month (SPY)
Status: REVIEWED: FAIL (frozen 2026-11-09, tested 2026-11-11)   Market: SPY   Holding: about 4-6 days a month
## Idea
Stock returns cluster around the turn of the month (pay-day flows). Hold SPY only then, cash otherwise.
## Sources
- Ariel (1987), JFE; Lakonishok & Smidt (1988), RFS; McConnell & Xu (2008), FAJ: from the last trading day through the
  third trading day of the month, US stocks earned essentially all of their excess return 1926-2005.
## Rules
Hold SPY for the open-to-open intervals starting on the last `m` trading days of a month or the first `p` trading days.
## Variants: (m, p) in {(1,3), (2,3), (1,4), (3,3)}
## Benchmark: SPY buy and hold. Random: rotated in/out path.
## Why it might fail
Widely known since the 1980s; the effect may be arbitraged. Lower total return than buy-and-hold by design.
Code: daily/strategies.py TurnOfMonth.

## Results (2026-11-11) -> research/results/E004.md
Best tom_m1_p4: +8.0%/yr, Sharpe 0.92 vs SPY 1.08 (in the market ~20% of days), 90% vs random. Valid -0.1%/yr.
