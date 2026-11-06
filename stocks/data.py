"""Stock 5-minute data for research: converts the Day-Trading-Lab download into compact numpy arrays.

Source: ../Day-Trading-Lab/lab/phase3/data/bars/*.json.gz (Alpaca sip feed, split-adjusted, regular session,
{date: [[slot, o, h, l, c, v], ...]}, slot 0 = 09:30, 77 = 15:55). Read only; nothing there is changed.
Cleaning rules are the lab's (PROTOCOL.md): early-close days, sessions with fewer than 60 real bars or no
09:30 bar, and sessions with a wick over 5% of the close (bad print) are marked invalid. Missing slots are
filled with the previous close (no future information).

Cache: stocks/cache/<SYM>.npz with dates (D,), bars float32 (D, 78, 5) [o,h,l,c,v], valid bool (D,).
"""
import datetime
import gzip
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SRC = os.path.join(os.path.dirname(ROOT), "Day-Trading-Lab", "lab", "phase3", "data", "bars")
CACHE = os.path.join(HERE, "cache")
SLOTS = 78
MIN_BARS, MAX_WICK = 60, 0.05

# Research periods. The holdout stays sealed until a rule is frozen (see stocks/PROTOCOL.md).
PERIODS = {"train": ("2016-04-01", "2021-12-31"), "valid": ("2022-01-01", "2023-12-31"),
           "holdout": ("2024-01-01", "2026-10-27")}


def early_closes(first_year=2016, last_year=2026):
    days = set()
    for y in range(first_year, last_year + 1):
        d = datetime.date(y, 11, 1)
        d += datetime.timedelta(days=(3 - d.weekday()) % 7)
        days.add(d + datetime.timedelta(weeks=3, days=1))
        dec24 = datetime.date(y, 12, 24)
        if dec24.weekday() < 5 and datetime.date(y, 12, 25).weekday() != 5:
            days.add(dec24)
        jul3 = datetime.date(y, 7, 3)
        if jul3.weekday() < 4:
            days.add(jul3)
    return {d.isoformat() for d in days}


EARLY = early_closes()


def convert(sym, src=SRC, cache=CACHE):
    with gzip.open(os.path.join(src, sym + ".json.gz"), "rt", encoding="utf-8") as fh:
        raw = json.load(fh)
    dates = sorted(raw)
    bars = np.zeros((len(dates), SLOTS, 5), dtype=np.float32)
    valid = np.zeros(len(dates), dtype=bool)
    for k, d in enumerate(dates):
        by = {b[0]: b for b in raw[d] if 0 <= b[0] < SLOTS}
        ok = d not in EARLY and len(by) >= MIN_BARS and 0 in by
        if ok and any(max((b[2] - max(b[1], b[4])) / b[4], (min(b[1], b[4]) - b[3]) / b[4]) > MAX_WICK
                      for b in by.values()):
            ok = False
        prev = by[0][1] if 0 in by else None
        for i in range(SLOTS):
            b = by.get(i)
            if b is None:
                bars[k, i] = (prev, prev, prev, prev, 0) if prev is not None else 0
            else:
                bars[k, i] = b[1:6]
                prev = b[4]
        valid[k] = ok
    np.savez(os.path.join(cache, sym + ".npz"), dates=np.array(dates), bars=bars, valid=valid)
    return len(dates), int(valid.sum())


def symbols(src=SRC):
    return sorted(f[:-8] for f in os.listdir(src) if f.endswith(".json.gz"))


class Universe:
    """All symbols aligned on one calendar. bars: (S, D, 78, 5) float32; valid: (S, D) bool."""

    def __init__(self, syms=None, cache=CACHE):
        syms = syms or sorted(f[:-4] for f in os.listdir(cache) if f.endswith(".npz"))
        per = {s: np.load(os.path.join(cache, s + ".npz")) for s in syms}
        all_dates = sorted(set().union(*(set(p["dates"].tolist()) for p in per.values())))
        idx = {d: k for k, d in enumerate(all_dates)}
        self.symbols, self.dates = syms, np.array(all_dates)
        self.bars = np.zeros((len(syms), len(all_dates), SLOTS, 5), dtype=np.float32)
        self.valid = np.zeros((len(syms), len(all_dates)), dtype=bool)
        for i, s in enumerate(syms):
            p = per[s]
            rows = np.array([idx[d] for d in p["dates"].tolist()])
            self.bars[i, rows] = p["bars"]
            self.valid[i, rows] = p["valid"]

    def day_range(self, first, last):
        return np.where((self.dates >= first) & (self.dates <= last))[0]


if __name__ == "__main__":
    # python -m stocks.data [START_INDEX COUNT]  (converts in chunks so each run stays short)
    os.makedirs(CACHE, exist_ok=True)
    syms = symbols()
    a = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    n = int(sys.argv[2]) if len(sys.argv) > 2 else len(syms)
    for s in syms[a:a + n]:
        if os.path.exists(os.path.join(CACHE, s + ".npz")):
            continue
        d, v = convert(s)
        print(s, d, v, flush=True)
