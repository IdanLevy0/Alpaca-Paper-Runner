"""Intraday stock strategies (rules exactly as in stocks/PROTOCOL.md). Shared by the backtest and the paper bot.

A strategy has: name, K (max positions), decision_slots, and select(ctx, slot, held) returning a list of
(symbol_index, stop_fraction or None, hold_bars), best first. ctx gives today's bars and precomputed features.
"""
import numpy as np


class Reversal:
    """H1: buy unusually sharp 60-minute drops (z <= -Z), exit after H bars, stop 2 sigma below entry."""
    decision_slots = (11, 23, 35, 47, 59)

    def __init__(self, Z=2.0, H=12, K=5):
        self.Z, self.H, self.K = Z, H, K
        self.name = f"reversal_z{Z:g}_h{H}"

    def scores(self, ctx, slot):
        """Last-60-minute return in units of sigma60. At 10:30 the last 60 minutes start at the 09:30 open
        (same definition as sigma60's first block). Never index slot - 12 when slot < 12: -1 would wrap to
        today's 15:55 bar, i.e. look into the future (the bug found on 2026-11-06)."""
        c = ctx["bars"][:, slot, 3].astype(np.float64)
        prev = (ctx["bars"][:, slot - 12, 3] if slot >= 12 else ctx["bars"][:, 0, 0]).astype(np.float64)
        with np.errstate(divide="ignore", invalid="ignore"):
            return (c / prev - 1) / ctx["sigma60"]

    def eligible(self, ctx, held, slot=None):
        ok = ctx["valid"] & np.isfinite(ctx["sigma60"]) & (ctx["sigma60"] > 0)
        ok[list(held)] = False
        return ok

    def select(self, ctx, slot, held):
        z = self.scores(ctx, slot)
        ok = self.eligible(ctx, held) & np.isfinite(z) & (z <= -self.Z)
        order = [i for i in np.argsort(z) if ok[i]]
        return [(i, 2.0 * ctx["sigma60"][i], self.H) for i in order]

    def params_for(self, ctx, i, slot=None):
        return 2.0 * ctx["sigma60"][i], self.H


class LateMomentum:
    """H2: at 15:30 buy the K stocks with the largest positive move from yesterday's close to 10:00; exit 15:55."""
    decision_slots = (71,)

    def __init__(self, K=5, market_filter=False):
        self.K, self.market_filter = K, market_filter
        self.name = f"latemom_k{K}" + ("_mkt" if market_filter else "")

    def scores(self, ctx, slot):
        with np.errstate(divide="ignore", invalid="ignore"):
            return ctx["bars"][:, 5, 3].astype(np.float64) / ctx["prev_close"] - 1

    def eligible(self, ctx, held, slot=None):
        ok = ctx["valid"] & np.isfinite(ctx["prev_close"])
        ok[list(held)] = False
        return ok

    def select(self, ctx, slot, held):
        s = self.scores(ctx, slot)
        ok = self.eligible(ctx, held) & np.isfinite(s)
        if self.market_filter and not (ok.any() and np.nanmean(np.where(ok, s, np.nan)) > 0):
            return []
        order = [i for i in np.argsort(-s) if ok[i] and s[i] > 0]
        return [(i, None, 77 - (slot + 1)) for i in order]

    def params_for(self, ctx, i, slot=None):
        return None, 77 - (71 + 1)


class GapGo:
    """H4 (card H004): gap up >= G on opening-30-minute relative volume >= R, buy when a decision bar closes above
    the first-30-minute high and above today's open. Stop at the first-30-minute low, exit at 15:55.
    Opening range = slots 0-5 only (09:30-10:00), so it never contains a decision bar."""
    decision_slots = (6, 12, 18)

    def __init__(self, G=0.01, R=2.0, K=5):
        self.G, self.R, self.K = G, R, K
        self.name = f"gapgo_g{G * 100:g}_r{R:g}"

    def scores(self, ctx, slot):
        """Relative volume of the first 30 minutes (ranking key)."""
        with np.errstate(divide="ignore", invalid="ignore"):
            return ctx["bars"][:, :6, 4].astype(np.float64).sum(axis=1) / ctx["open_vol_base"]

    def eligible(self, ctx, held, slot=None):
        ok = (ctx["valid"] & np.isfinite(ctx["prev_close"]) & (ctx["prev_close"] > 0)
              & np.isfinite(ctx["open_vol_base"]) & (ctx["open_vol_base"] > 0))
        ok[list(held | ctx.get("entered", set()))] = False
        return ok

    def select(self, ctx, slot, held):
        b = ctx["bars"].astype(np.float64)
        rv = self.scores(ctx, slot)
        with np.errstate(divide="ignore", invalid="ignore"):
            gap = b[:, 0, 0] / ctx["prev_close"] - 1
        or_high, or_low, c = b[:, :6, 1].max(axis=1), b[:, :6, 2].min(axis=1), b[:, slot, 3]
        ok = (self.eligible(ctx, held) & np.isfinite(rv) & (gap >= self.G) & (rv >= self.R)
              & (c > or_high) & (c > b[:, 0, 0]))
        order = [i for i in np.argsort(-rv, kind="stable") if ok[i]]
        return [(i, None, 77 - (slot + 1), float(or_low[i])) for i in order]

    def params_for(self, ctx, i, slot):
        return None, 77 - (slot + 1), float(ctx["bars"][i, :6, 2].min())


class VolSpike:
    """H5 (card H005): a 5-minute bar with volume >= R x that slot's 20-session average that closes up and in the top
    quarter of its range. Buy next open, hold H bars (or to 15:55), stop at the spike bar's low."""
    decision_slots = tuple(range(6, 53))

    def __init__(self, R=4.0, H=6, K=5):
        self.R, self.H, self.K = R, H, K
        self.name = f"volspike_r{R:g}_h{H}"

    def scores(self, ctx, slot):
        base = ctx["slot_vol_base"][:, slot].astype(np.float64)
        with np.errstate(divide="ignore", invalid="ignore"):
            return ctx["bars"][:, slot, 4].astype(np.float64) / base

    def eligible(self, ctx, held, slot=None):
        ok = ctx["valid"].copy()
        if slot is not None:
            base = ctx["slot_vol_base"][:, slot]
            ok &= np.isfinite(base) & (base > 0)
        ok[list(held | ctx.get("entered", set()))] = False
        return ok

    def select(self, ctx, slot, held):
        o, h, l, c = (ctx["bars"][:, slot, k].astype(np.float64) for k in range(4))
        ratio = self.scores(ctx, slot)
        rng = h - l
        with np.errstate(divide="ignore", invalid="ignore"):
            pos = np.where(rng > 0, (c - l) / rng, 0.0)
        ok = (self.eligible(ctx, held, slot) & np.isfinite(ratio) & (ratio >= self.R) & (c > o)
              & (rng > 0) & (pos >= 0.75))
        order = [i for i in np.argsort(-ratio, kind="stable") if ok[i]]
        return [(i, None, self.H, float(l[i])) for i in order]

    def params_for(self, ctx, i, slot):
        return None, self.H, float(ctx["bars"][i, slot, 2])


# Hypothesis cards (research/cards/H###-*.md) -> the exact variants pre-registered on that card.
# The Quant agent adds a new entry here when a card is approved; existing entries are never edited.
CARDS = {
    "H001": lambda: [Reversal(Z, H) for Z in (2.0, 3.0) for H in (12, 24)],
    "H002": lambda: [LateMomentum(K, m) for K in (5, 10) for m in (False, True)],
    "H004": lambda: [GapGo(G, R) for G in (0.01, 0.02) for R in (2.0, 3.0)],
    "H005": lambda: [VolSpike(R, H) for R in (4.0, 8.0) for H in (6, 12)],
}


def variants(card=None):
    if card:
        return CARDS[card]()
    return CARDS["H001"]() + CARDS["H002"]()
