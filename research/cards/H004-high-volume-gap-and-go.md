# H004: high-volume gap-and-go (opening range breakout)
Status: FROZEN
Market: stocks (100 large caps)      Holding: minutes/hours, flat by 15:55
Drafted by researcher on 2026-11-06

## Idea (2-3 plain sentences)
A stock that opens well above yesterday's close on unusually heavy volume has news or big buyers behind it. If it
then holds above its opening price and breaks above the first 30-minute high, buy it and ride the day's
continuation until 15:55. This is different from H001 (buying drops) and H002 (late-day index momentum): it trades
a single stock's own opening event, only when volume confirms.

## Sources (opened, with what each actually measured)
- [Gervais, Kaniel, Mingelgrin (2001), The High-Volume Return Premium, via author page](https://sites.duke.edu/sgervais/?p=64): US stocks; stocks with unusually high volume over a day or a week tend to rise over the NEXT MONTH. Period, size and costs not shown on the page I opened. It is a monthly effect, not intraday, so using it for intraday is an extrapolation (weak support).
- [LuxAlgo, Gap and Go](https://www.luxalgo.com/library/concept/gap-and-go/): practitioner description only. Setup lives in the first 30-90 minutes, needs a gap of "at least a few percent", heavy relative volume, entry on a break of the opening-range high, and is invalid if price falls back toward the prior close. It gives NO statistics, win rates or costs.
- A search for peer-reviewed intraday evidence on high-volume opening gaps found none I could open (the one 2025 MDPI paper on weekend gaps returned HTTP 403). So the evidence for this card is thin; the test is meant to find out.

## Rules (exact; another agent must be able to code this with no judgment calls)
Slots: 78 five-minute bars per day, slot 0 = 09:30 bar, slot 5 = 09:55 bar (ends 10:00), slot 77 = 15:55 bar.
- gap = open of slot 0 / previous valid close - 1.
- OR_high / OR_low = highest high / lowest low of slots 0-5 (the first 30 minutes).
- RV (relative volume) = sum of volume in slots 0-5 today / mean of the same sum over the prior 20 valid sessions.
- Decision times: closes of slots 6, 12, 18 (10:05, 10:35, 11:05), so the opening range (slots 0-5) is complete
  and never includes the decision bar. Entries are at the next bar's open.
- Signal (all must hold at the decision close): gap >= G; RV >= R; close of the decision bar > OR_high;
  close of the decision bar > today's open (slot 0 open); stock not held and not already entered today.
- Entry: next bar open (at most one entry per stock per day).
- Exit: stop at OR_low (checked on 5-minute lows; a bar opening below it exits at its open, per PROTOCOL);
  otherwise exit at the open of the 15:55 bar (slot 77).
- Max positions K = 5, each 1/5 of equity. If more than K qualify at one time, take the highest RV first.
- Costs: 0.03% per side = 6 bps round trip (PROTOCOL base). Also report 0% and 0.05%/side. Stops may fill worse than
  modelled; the 0.05% sensitivity covers that.

## Variants (max 4)
1. G = 1.0%, R = 2.0
2. G = 1.0%, R = 3.0
3. G = 2.0%, R = 2.0
4. G = 2.0%, R = 3.0

## Why it might work
- Large gaps on heavy volume usually come with news (earnings, upgrades); information is absorbed over hours, not seconds.
- Requiring a break of the opening range filters out gaps that are already fading.
- Expected edge: unknown, no published number. To beat 6 bps round trip plus stop slippage, the average trade needs
  about +10 bps net of everything. Only a handful of the 100 stocks gap 1-2% on 2x volume each day, so expect few
  trades (maybe 0-3 per day) and a noisy result.

## Why it might fail (be specific)
- Many gap days are earnings days, and large caps often reverse after the first hour (gap-fill). The practitioner
  guide itself says the fill playbook is the alternative.
- Few trades means low statistical power; the Skeptic will probably say the sample is small even over 2016-2021.
- Survivorship bias (stocks listed today) flatters gap-up stocks.
- Stop at OR_low can be wide (several %), so one loser can cancel several winners.
- The first 30 minutes are the widest-spread time of day; real fills at the 10:00-11:00 entries may be worse than 3 bps.
- Source evidence is monthly horizon and anecdotal; the idea is a hypothesis, not a replication.

## Data needed (and whether we already have it)
5-minute OHLCV for 100 stocks: have it. Previous valid close: have it (ctx prev_close).

## Coding notes (quant, written before running)
Needs NEW code in stocks/strategies.py: a new strategy class (not Reversal/LateMomentum) and a precomputed
per-stock "mean opening-30-minute volume over prior 20 valid sessions" feature in ctx (ctx currently only exposes
sigma60 and prev_close as far as I could see). Volume is assumed to be in the bars array; quant to confirm.
Register as CARDS["H004"] with the 4 variants above. The look-ahead trap: never index slot-N with slot < N (the
2026-11-06 bug); OR_high uses slots 0-5 only, never the decision bar.

## Frozen 2026-11-07 (before any result)
Code: stocks/strategies.py GapGo, CARDS["H004"]; features in stocks/features.py; tests in tests/test_volume_cards.py
(look-ahead scramble, prior-sessions-only volume baselines, stop at a fixed price level, one entry per stock per day).
Coding choices the card left open: the opening range stays slots 0-5 at every decision (not updated later); ties in RV keep symbol order.
Gates as in stocks/PROTOCOL.md: best variant on train after 0.03%/side must have p < 0.05 and beat >= 90% of random
runs (same times and counts, random eligible stocks, same stop/exit formula), then be positive on validation 2022-23.
The holdout stays sealed. If the sign comes out reversed, that is logged as a finding, not traded: a reversed rule
would be a new card.

## Results (quant, after running)  -> research/results/H004.md

## Skeptic review
