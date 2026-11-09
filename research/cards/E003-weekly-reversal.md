# E003: Weekly reversal in large caps
Status: FROZEN (2026-11-09, before any result)   Market: the 100 stocks   Holding: 1 week
## Idea
Last week's biggest losers tend to bounce next week (overreaction / liquidity). The multi-day cousin of H001,
where costs are small compared with weekly moves.
## Sources
- Lehmann (1990), "Fads, Martingales, and Market Efficiency", QJE: weekly losers outperform winners the next week.
- Jegadeesh (1990), JF: 1-month reversal.  - Nagel (2012), RFS: reversal profits as liquidity provision.
## Rules
At each week's last close: L-day return for each stock; hold the N lowest equal weight until next week's last close.
## Variants: N in {5, 10} x L in {5, 10}
## Benchmark: all 100 equal weight monthly. Random: N random stocks each week.
## Why it might fail
The effect has shrunk a lot in large caps since the 1990s; ~100% weekly turnover costs ~3%/yr at 0.03%/side.
Code: daily/strategies.py WeeklyReversal.
