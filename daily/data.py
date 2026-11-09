"""Daily bars as aligned arrays. Stocks + ETFs share one NYSE calendar; BTC (7 days a week) is its own panel.

Panel: symbols, dates (str, all trading days in the file set), o/h/l/c/v float64 (N, D) with NaN where missing.
History(panel, t): read-only view of everything known at the CLOSE of day t (prices through t, plus the trading
calendar, which is known in advance). Strategies only ever receive a History, so they cannot read future prices.
"""
import json
import os

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, "cache")


class Panel:
    def __init__(self, symbols, dates, o, h, l, c, v, etf=None):
        self.symbols, self.dates = list(symbols), np.asarray(dates)
        self.o, self.h, self.l, self.c, self.v = o, h, l, c, v
        self.etf = etf if etf is not None else np.zeros(len(self.symbols), dtype=bool)
        self.index = {s: i for i, s in enumerate(self.symbols)}

    def idx(self, names):
        return [self.index[s] for s in names if s in self.index]

    def day(self, date):
        """First index with dates >= date."""
        return int(np.searchsorted(self.dates, date))


def load(kind="stock", cache=CACHE):
    files = [json.load(open(os.path.join(cache, f))) for f in sorted(os.listdir(cache)) if f.endswith(".json")]
    files = [f for f in files if f["kind"] == kind and f["bars"]]
    dates = sorted({b[0] for f in files for b in f["bars"]})
    pos = {d: k for k, d in enumerate(dates)}
    N, D = len(files), len(dates)
    arr = {k: np.full((N, D), np.nan) for k in "ohlcv"}
    for i, f in enumerate(files):
        cols = np.array([b[1:] for b in f["bars"]], dtype=float)
        rows = np.array([pos[b[0]] for b in f["bars"]])
        for j, k in enumerate("ohlcv"):
            arr[k][i, rows] = cols[:, j]
    return Panel([f["symbol"] for f in files], dates, arr["o"], arr["h"], arr["l"], arr["c"], arr["v"],
                 np.array([bool(f.get("etf")) for f in files]))


class History:
    """What a strategy may see at the close of day t."""

    def __init__(self, panel, t):
        self.t, self.panel = t, panel
        self.c = panel.c[:, :t + 1]
        self.o = panel.o[:, :t + 1]
        self.date = panel.dates[t]
        self.calendar = panel.dates          # dates only (holidays are published in advance), no prices
        self.symbols = panel.symbols

    def next_date(self):
        return self.calendar[self.t + 1] if self.t + 1 < len(self.calendar) else None
