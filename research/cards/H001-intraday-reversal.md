# H001: Intraday reversal after an unusually sharp drop
Status: REVIEWED (FAIL)
Market: stocks (100 large caps)      Holding: 1-2 hours, flat by 15:55
Pre-registered in stocks/PROTOCOL.md (commit 097cb24, 2026-11-06) before any result.

## Idea
When a large stock falls much more than usual in an hour, part of the drop is often liquidity-driven (forced or
impatient sellers) and partly bounces back. Buy the sharpest drops and hold 1-2 hours.

## Sources
- Heston, Korajczyk & Sadka (2010), intraday patterns in the cross-section of returns.
- Nagel (2012), "Evaporating Liquidity": short-term reversal as a return for providing liquidity.

## Rules
See stocks/PROTOCOL.md H1. Decisions 10:30, 11:30, 12:30, 13:30, 14:30; z = last-60-min return / sigma60;
buy most negative z if z <= -Z; exit after H bars or 15:55; stop 2 x sigma60; K = 5.

## Variants
Z in {2, 3} x H in {12, 24 bars}.

## Coding notes
First run showed +0.69%/day: look-ahead bug (slot - 12 = -1 wrapped to the 15:55 close at the 10:30 decision).
Fixed: 10:30 uses the 09:30 open. Regression test scrambles all later bars; it fails on the buggy code.

## Results (train 2016-04..2021, 0.03%/side) -> STOCK_RESEARCH_REPORT.md
| Variant | Before costs | After costs | Trades/day |
|---|---|---|---|
| z2 h12 | +1.58bp/day | -6.41bp/day | 6.7 |
| z2 h24 | +2.19bp/day | -5.25bp/day | 6.2 |
| z3 h12 | +0.78bp/day | -3.35bp/day | 3.4 |
| z3 h24 (best) | +1.11bp/day | -2.96bp/day | 3.4 |
Best: luck p 0.989 after costs, beats 94% of random-stock runs, validation 2022-23 -2.56bp/day.

## Skeptic review (written by Claude in the setup chat)
FAIL at gate 1. The entry rule picks better stocks than random (94th percentile), so there is a small real
effect before costs, but it is about a quarter of the cost. Follow-ups worth a new card: cheaper execution
(limit orders) or fewer, larger moves.
