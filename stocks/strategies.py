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

    def eligible(self, ctx, held):
        ok = ctx["valid"] & np.isfinite(ctx["sigma60"]) & (ctx["sigma60"] > 0)
        ok[list(held)] = False
        return ok

    def select(self, ctx, slot, held):
        z = self.scores(ctx, slot)
        ok = self.eligible(ctx, held) & np.isfinite(z) & (z <= -self.Z)
        order = [i for i in np.argsort(z) if ok[i]]
        return [(i, 2.0 * ctx["sigma60"][i], self.H) for i in order]

    def params_for(self, ctx, i):
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

    def eligible(self, ctx, held):
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

    def params_for(self, ctx, i):
        return None, 77 - (71 + 1)


# Hypothesis cards (research/cards/H###-*.md) -> the exact variants pre-registered on that card.
# The Quant agent adds a new entry here when a card is approved; existing entries are never edited.
CARDS = {
    "H001": lambda: [Reversal(Z, H) for Z in (2.0, 3.0) for H in (12, 24)],
    "H002": lambda: [LateMomentum(K, m) for K in (5, 10) for m in (False, True)],
}


def variants(card=None):
    if card:
        return CARDS[card]()
    return CARDS["H001"]() + CARDS["H002"]()
