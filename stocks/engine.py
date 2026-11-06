"""Intraday multi-stock backtest (rules in stocks/PROTOCOL.md).

Per day: walk the strategy's decision slots in order. At a decision (bar close at `slot`), positions whose
exit slot is <= slot are already closed, so capacity is K minus positions still open. New positions enter
at the open of slot+1 and leave at the open of min(slot+1+hold, 77) unless the stop is hit first
(checked on 5-minute lows from the entry bar on; a bar opening below the stop exits at its open).
Daily portfolio return = sum of trade returns / K. The holdout is refused unless allow_holdout=True.
"""
import numpy as np

from stocks.data import PERIODS

COST = 0.0003
FLAT_SLOT = 77


class SealedHoldout(Exception):
    pass


def simulate_trade(day_bars, i, entry_slot, exit_slot, stop_frac, cost):
    o, l = day_bars[i, :, 0].astype(np.float64), day_bars[i, :, 2].astype(np.float64)
    raw_entry = o[entry_slot]
    stop = raw_entry * (1 - stop_frac) if stop_frac else None
    px, reason, xs = o[exit_slot], "time", exit_slot
    if stop is not None:
        lows = l[entry_slot:exit_slot]
        hit = np.where(lows <= stop)[0]
        if len(hit):
            xs = entry_slot + int(hit[0])
            px, reason = min(stop, o[xs]), "stop"
    ret = (px * (1 - cost)) / (raw_entry * (1 + cost)) - 1
    return {"sym": i, "entry_slot": entry_slot, "exit_slot": xs, "entry": raw_entry, "exit": px,
            "reason": reason, "ret": ret}


def run(u, feats, strategy, first, last, cost=COST, allow_holdout=False, picker=None):
    """Returns (daily list of (date, return, n_trades), trades list). picker(ctx, slot, held, picks) can
    replace the strategy's chosen symbols (used by the random baseline)."""
    if last >= PERIODS["holdout"][0] and not allow_holdout:
        raise SealedHoldout("the holdout is sealed until a rule is frozen and Idan agrees")
    days = u.day_range(first, last)
    daily, trades = [], []
    for d in days:
        ctx = {"bars": u.bars[:, d], "valid": u.valid[:, d].copy(), "date": u.dates[d],
               "sigma60": feats["sigma60"][:, d], "prev_close": feats["prev_close"][:, d]}
        if not ctx["valid"].any():
            continue
        open_pos, day_tr = [], []
        for slot in strategy.decision_slots:
            open_pos = [p for p in open_pos if p["exit_slot"] > slot]
            room = strategy.K - len(open_pos)
            if room <= 0:
                continue
            held = {p["sym"] for p in open_pos}
            picks = strategy.select(ctx, slot, held)[:room]
            if picker is not None:
                picks = picker(ctx, slot, held, picks)
            for i, stop_frac, hold in picks:
                es = slot + 1
                t = simulate_trade(ctx["bars"], i, es, min(es + hold, FLAT_SLOT), stop_frac, cost)
                t["date"] = ctx["date"]
                open_pos.append(t)
                day_tr.append(t)
        trades.extend(day_tr)
        daily.append((ctx["date"], sum(t["ret"] for t in day_tr) / strategy.K, len(day_tr)))
    return daily, trades


def random_picker(strategy, rng):
    """Same number of picks at the same times, random eligible stocks, same hold/stop formula."""
    def pick(ctx, slot, held, picks):
        if not picks:
            return []
        pool = np.where(strategy.eligible(ctx, held))[0]
        chosen = rng.choice(pool, size=min(len(picks), len(pool)), replace=False)
        return [(int(i), *strategy.params_for(ctx, int(i))) for i in chosen]
    return pick
