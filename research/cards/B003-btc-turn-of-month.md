# B003: BTC turn of the month
Status: REVIEWED: FAIL (close) (frozen 2026-11-09, tested 2026-11-11)   Market: BTC/USD   Holding: about 6 days a month
## Idea
From the library: "L1 Turn-of-the-Month Long (crypto calendar effect)": its trades enter ~4-5 days before month end and
exit on day 2. Our rules: hold from `m` calendar days before the month's last day through calendar day `p`.
## Variants: (m, p) in {(4,2), (2,2), (4,4), (6,2)}
## Benchmark: BTC buy and hold. Random: rotated in/out path.
## Why it might fail: no academic evidence for crypto; 53 trades in the library sample; 0.5% per round trip.

## Results (2026-11-11) -> research/results/B003.md
Best btc_tom_m4_p2: +26.8%/yr vs BTC -25%/yr on 2021-22, beats 98% of random, but p 0.076 on only 2 years of data. Valid 2023 +14.9% (BTC +155%).
