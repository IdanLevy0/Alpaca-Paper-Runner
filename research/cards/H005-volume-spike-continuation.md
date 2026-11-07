# H005: volume-spike continuation (5-minute bar)
Status: REVIEWED: FAIL
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

## Frozen 2026-11-07 (before any result)
Code: stocks/strategies.py VolSpike, CARDS["H005"]; features in stocks/features.py; tests in tests/test_volume_cards.py
(look-ahead scramble, prior-sessions-only volume baselines, stop at a fixed price level, one entry per stock per day).
Coding choices the card left open: a slot with zero or missing 20-session base volume is not eligible; ties keep symbol order; if the next bar opens below the spike low the trade exits at that open (PROTOCOL stop rule).
Gates as in stocks/PROTOCOL.md: best variant on train after 0.03%/side must have p < 0.05 and beat >= 90% of random
runs (same times and counts, random eligible stocks, same stop/exit formula), then be positive on validation 2022-23.
The holdout stays sealed. If the sign comes out reversed, that is logged as a finding, not traded: a reversed rule
would be a new card.

## Results (quant, after running)  -> research/results/H005.md
Run 2026-11-07, train 2016-04..2021-12, base cost 0.03%/side.
- Before costs the edge is essentially zero: +0.2 to +1.3bp/day, under +1bp per trade. At 4x volume the rule fires
  about 9 times a day, so costs (6bp a round trip) turn it into -10bp/day (about -23% a year).
- Best: volspike_r8_h6. -1.49bp/day after costs, -4.1bp per trade, 37% winners. Luck p-value 0.997. Random picks with
  the same timing and the same tight stop do even worse (it beats 100% of them), so the volume filter isn't useless,
  it just doesn't earn enough to pay for trading. Negative in 5 of 6 train years. Validation 2022-23: -2.34bp/day.
- Gate 1: FAIL.

## Skeptic review
Verdict: FAIL (2026-11-07). No continuation worth trading after a 5-minute volume spike in large caps. The tight stop
(spike bar's low) gets hit often (37% winners), which is the "stop triggers on noise" risk the card predicted. Not
worth re-running with other thresholds: the before-cost edge is too small for any version to clear 6bp a trade.
