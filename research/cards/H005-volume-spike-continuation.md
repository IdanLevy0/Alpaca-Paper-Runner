# H005: volume-spike continuation (5-minute bar)
Status: DRAFT
Market: stocks (100 large caps)      Holding: 30-60 minutes (or to 15:55), flat by 15:55
Drafted by researcher on 2026-11-06

## Idea (2-3 plain sentences)
When one 5-minute bar trades several times its normal volume AND closes up near its high, big buyers are probably
active and not finished. Buy the next bar and hold for 30 or 60 minutes. Unlike H004 this works any time of day, on
any stock, with no gap needed; unlike H001 it buys strength with volume, not weakness.

## Sources (opened, with what each actually measured)
- [Gervais, Kaniel, Mingelgrin (2001), The High-Volume Return Premium, via author page](https://sites.duke.edu/sgervais/?p=64): US stocks; unusually high volume over a day or a week is followed by higher returns over the next month. Size, period and costs are not on the page I opened. Monthly horizon, so applying it to 5-minute bars is an extrapolation.
- [LuxAlgo, Gap and Go](https://www.luxalgo.com/library/concept/gap-and-go/): practitioners want a break "on expanding volume" for continuation. No statistics given.
- No source I could open tests 5-minute volume spikes with a 30-60 minute hold. This is a weakly supported, exploratory card. Also note GKM's own explanation (visibility / attention) is slow-moving, so the intraday effect could be zero or even reverse (H001 found short-term reversal after sharp drops, which is the opposite sign).

## Rules (exact; another agent must be able to code this with no judgment calls)
Slots: 78 bars per day, slot 0 = 09:30 bar, slot 77 = 15:55 bar.
- baseVol[stock, slot] = mean volume of that same slot over the prior 20 valid sessions.
- Decision times: closes of slots 6 to 52 (10:05 to 13:55), every bar. Entry at the next bar's open.
- Signal at a decision close (all must hold): volume of the bar / baseVol >= R; bar close > bar open;
  (close - low) / (high - low) >= 0.75 (high - low > 0); stock not held; at most one entry per stock per day.
- Exit: after H bars from entry, or at the open of the 15:55 bar, whichever is first. Stop at the low of the spike
  bar (checked on 5-minute lows; a bar opening below it exits at its open).
- Max positions K = 5, each 1/5 of equity. If more than K qualify at the same close, take the largest volume ratio.
- Costs: 0.03% per side = 6 bps round trip (PROTOCOL base); also report 0% and 0.05%/side.

## Variants (max 4)
1. R = 4, H = 6 bars (30 min)
2. R = 4, H = 12 bars (60 min)
3. R = 8, H = 6 bars
4. R = 8, H = 12 bars

## Why it might work
- Large orders are split over minutes, so a volume burst with a strong close can mean more buying follows.
- Attention effect from the high-volume literature (slow-moving, but same direction).
- Expected edge: unknown. Needs roughly +6 bps gross per trade just to break even on costs, plus a bit more for
  stop slippage. H001 showed a +1.1 bp/day gross edge was swallowed by costs, so the bar is high.

## Why it might fail (be specific)
- A spike bar's close is already after the move; the next open may be the exhaustion point (short-term reversal,
  the thing H001 exploits).
- Volume spikes cluster at news, index rebalances and the open; the slot-matched baseline handles time of day
  but not event days, where the price jumps and mean-reverts.
- Many trades per day with 6 bps round-trip cost compounds the drag; H001 cost about 4 bp/day.
- Stop at the spike bar's low is tight (often under 0.3%) and will trigger on noise.
- With 4 variants and thousands of trades, a small bias in costs (spread widens exactly on spikes) can flip the sign.

## Data needed (and whether we already have it)
5-minute OHLCV for 100 stocks: have it.

## Coding notes (quant, written before running)
Needs NEW code in stocks/strategies.py: a new class plus a precomputed per-stock, per-slot "mean volume over prior
20 valid sessions" array in ctx (not present in the Reversal/LateMomentum code I read). Confirm volume is index 4 of
the bars array. Slot-level selection with sorting by volume ratio mirrors Reversal.select. Register as CARDS["H005"].
Watch for look-ahead: baseVol must use prior sessions only, and the decision bar's own volume is allowed (bar is closed).
Zero-volume baseline must be skipped (not eligible).

## Results (quant, after running)  -> research/results/H005.md

## Skeptic review
