"""Multi-day backtest on daily bars (rules in daily/PROTOCOL.md).

A strategy decides at the CLOSE of day t (seeing only History(panel, t)) and returns either None (no change) or a
target weight vector (N,) summing to <= 1; the rest is cash (0% interest). Orders fill at the OPEN of day t+1.
Positions are tracked in dollars, drift with prices, and pay `cost` per side on every dollar traded.
Return series: one value per holding interval [open d, open d+1], labelled with day d.
"""
import numpy as np

STOCK_PERIODS = {"train": ("2016-04-01", "2021-12-31"), "valid": ("2022-01-01", "2023-12-31"),
                 "holdout": ("2024-01-01", "2099-01-01")}


class SealedHoldout(Exception):
    pass


def decide(panel, strategy, t0, t1):
    """Weights W (D, N) after each close in [t0, t1] and a rebalance mask R (D,). Uses History only."""
    from daily.data import History
    D, N = len(panel.dates), len(panel.symbols)
    W, R = np.zeros((D, N)), np.zeros(D, dtype=bool)
    cur = np.zeros(N)
    for t in range(t0, t1 + 1):
        w = strategy.weights(History(panel, t))
        if w is not None:
            w = np.nan_to_num(np.asarray(w, dtype=float))
            assert w.min() >= -1e-12 and w.sum() <= 1 + 1e-9, "long only, no leverage"
            cur, R[t] = w, True
        W[t] = cur
    return W, R


def simulate(panel, W, R, first, last, cost, holdout_start=None, allow_holdout=False, periods_per_year=252):
    """Daily returns for holding intervals starting on days in [first, last] (dates). Returns (dates, rets, turnover)."""
    if holdout_start and last >= holdout_start and not allow_holdout:
        raise SealedHoldout("the holdout is sealed until a rule is frozen and Idan agrees")
    a = panel.day(first)
    b = int(np.searchsorted(panel.dates, last, side="right")) - 2   # last interval ends at the open of the last day <= last
    o = panel.o
    pos, cash = np.zeros(len(panel.symbols)), 1.0
    dates, rets, traded = [], [], 0.0
    for d in range(a, b + 1):   # interval [open d, open d+1], d+1 <= last
        # the decision made at the close of d-1 fills at the open of d
        eq = cash + pos.sum()
        if d - 1 >= 0 and (R[d - 1] or d == a):         # day one of a window starts from the current targets
            target = W[d - 1] * eq
            can = np.isfinite(o[:, d])
            target = np.where(can, target, pos)          # an asset with no open today cannot be traded
            trade = np.abs(target - pos).sum()
            cash -= (target - pos).sum() + trade * cost
            traded += trade / max(eq, 1e-12)
            pos = target
        with np.errstate(divide="ignore", invalid="ignore"):
            g = o[:, d + 1] / o[:, d]
        g = np.where(np.isfinite(g) & (g > 0), g, 1.0)
        pos = pos * g
        end = cash + pos.sum()
        dates.append(panel.dates[d])
        rets.append(end / eq - 1)                       # trading costs paid at today's open count today
    years = max(1e-9, len(rets) / periods_per_year)
    return np.array(dates), np.array(rets), traded / years


def shifted(W, R, t0, t1, k):
    """Random-timing baseline: rotate the weight path and the rebalance days inside [t0, t1] by k days."""
    W2, R2 = W.copy(), R.copy()
    W2[t0:t1 + 1] = np.roll(W[t0:t1 + 1], k, axis=0)
    R2[t0:t1 + 1] = np.roll(R[t0:t1 + 1], k)
    if t0 <= t1:
        R2[t0] = True
    return W2, R2


def stats(rets, periods_per_year=252, turnover=None, W=None):
    r = np.asarray(rets, dtype=float)
    if len(r) == 0:
        return {}
    eq = np.cumprod(1 + r)
    sd = r.std()
    out = {"days": len(r), "mean_bp": r.mean() * 1e4, "total_pct": (eq[-1] - 1) * 100,
           "cagr_pct": (eq[-1] ** (periods_per_year / len(r)) - 1) * 100,
           "vol_pct": sd * np.sqrt(periods_per_year) * 100,
           "sharpe": r.mean() / sd * np.sqrt(periods_per_year) if sd > 0 else 0.0,
           "max_dd_pct": float(np.max(1 - eq / np.maximum.accumulate(eq))) * 100}
    if turnover is not None:
        out["turnover"] = turnover
    return out


def boot_p(rets, n=5000, seed=3):
    r = np.asarray(rets)
    if len(r) < 20:
        return None
    rng, m = np.random.default_rng(seed), r.mean()
    c = r - m
    means = c[rng.integers(0, len(c), size=(n, len(c)))].mean(axis=1)
    return float((means >= m).mean())


def by_year(dates, rets):
    out = {}
    for d, r in zip(dates, rets):
        out.setdefault(str(d)[:4], []).append(r)
    return {y: (np.prod(1 + np.array(v)) - 1) * 100 for y, v in out.items()}
