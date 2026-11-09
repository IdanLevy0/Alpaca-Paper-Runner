# B003: BTC turn of the month
Status: FROZEN (2026-11-09, before any result)   Market: BTC/USD   Holding: about 6 days a month
## Idea
From the library: "L1 Turn-of-the-Month Long (crypto calendar effect)": its trades enter ~4-5 days before month end and
exit on day 2. Our rules: hold from `m` calendar days before the month's last day through calendar day `p`.
## Variants: (m, p) in {(4,2), (2,2), (4,4), (6,2)}
## Benchmark: BTC buy and hold. Random: rotated in/out path.
## Why it might fail: no academic evidence for crypto; 53 trades in the library sample; 0.5% per round trip.
