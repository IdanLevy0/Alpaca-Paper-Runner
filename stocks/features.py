"""Per-stock, per-day features. Every value for day d uses only data available at that point in day d."""
import numpy as np

BLOCK_ENDS = [11, 23, 35, 47, 59, 71]   # closes at 10:30, 11:30, 12:30, 13:30, 14:30, 15:30


def prev_close(u):
    """(S, D): close of the stock's previous VALID session (NaN if none)."""
    S, D = u.valid.shape
    out = np.full((S, D), np.nan, dtype=np.float64)
    last = np.full(S, np.nan)
    for d in range(D):
        out[:, d] = last
        v = u.valid[:, d]
        last = np.where(v, u.bars[:, d, 77, 3], last)
    return out


def sigma60(u, lookback=20):
    """(S, D): RMS of 60-minute block returns over the prior `lookback` valid sessions (NaN until enough)."""
    c, o = u.bars[..., 3].astype(np.float64), u.bars[..., 0].astype(np.float64)
    starts = np.concatenate([o[:, :, :1], c[:, :, BLOCK_ENDS[:-1]]], axis=2)
    with np.errstate(divide="ignore", invalid="ignore"):    # days a stock is absent are all zeros
        r2 = (c[:, :, BLOCK_ENDS] / starts - 1) ** 2        # (S, D, 6)
    day_sum = r2.sum(axis=2)
    S, D = u.valid.shape
    out = np.full((S, D), np.nan)
    for s in range(S):
        idx = np.where(u.valid[s])[0]
        cs = np.concatenate([[0.0], np.cumsum(day_sum[s, idx])])
        for j in range(lookback, len(idx)):
            out[s, idx[j]] = np.sqrt((cs[j] - cs[j - lookback]) / (lookback * 6))
    return out


def market_split(u, pc):
    """Equal-weight daily overnight and intraday returns across valid stocks: (dates, overnight, intraday)."""
    o, c = u.bars[:, :, 0, 0].astype(np.float64), u.bars[:, :, 77, 3].astype(np.float64)
    ok = u.valid & np.isfinite(pc)
    with np.errstate(divide="ignore", invalid="ignore"):
        on = np.where(ok, o / pc - 1, np.nan)
        intra = np.where(u.valid, c / o - 1, np.nan)
    return u.dates, np.nanmean(on, axis=0), np.nanmean(intra, axis=0)
