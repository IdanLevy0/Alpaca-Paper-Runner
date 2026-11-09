"""Multi-day strategies (rules exactly as on their cards, research/cards/E###-*.md and B###-*.md).

weights(h) is called at the close of every day with h = daily.data.History. It returns None (keep positions) or a
target weight vector over the panel's symbols (long only, sum <= 1, rest in cash). Fills happen at the next open.
Selection strategies also have random_weights(h, rng) for the random-picks baseline (same schedule, random names).
"""
import numpy as np

FABER5 = ["SPY", "EFA", "IEF", "VNQ", "DBC"]


def month_end(h):
    n = h.next_date()
    return n is not None and n[:7] != h.date[:7]


def week_end(h):
    import datetime
    n = h.next_date()
    if n is None:
        return False
    a = datetime.date.fromisoformat(h.date).isocalendar()[:2]
    b = datetime.date.fromisoformat(n).isocalendar()[:2]
    return a != b


def trading_day_of_month(h, k):
    """Position of calendar day k: +1 = first trading day of its month, -1 = last."""
    cal, d = h.calendar, h.calendar[k]
    lo = k
    while lo > 0 and cal[lo - 1][:7] == d[:7]:
        lo -= 1
    hi = k
    while hi + 1 < len(cal) and cal[hi + 1][:7] == d[:7]:
        hi += 1
    return k - lo + 1, -(hi - k + 1)


class Benchmark:
    """Equal weight in the given symbols (or all non-ETF stocks), rebalanced at month ends. Not a card."""
    kind = "random_none"

    def __init__(self, symbols=None, label="equal weight"):
        self.symbols, self.name = symbols, f"benchmark: {label}"

    def weights(self, h):
        if not (month_end(h) or h.t == 0):
            return None
        N = len(h.symbols)
        idx = h.panel.idx(self.symbols) if self.symbols else [i for i in range(N) if not h.panel.etf[i]]
        ok = [i for i in idx if np.isfinite(h.c[i, -1])]
        w = np.zeros(N)
        if ok:
            w[ok] = 1.0 / len(ok)
        return w


class TrendETF:
    """E1: each of the Faber-5 ETFs gets 1/5 when its trend is up, else that 1/5 sits in cash."""
    kind = "timing"

    def __init__(self, signal="sma200", check="month"):
        self.signal, self.check = signal, check
        self.name = f"trend_{signal}_{check}"

    def weights(self, h):
        if not (month_end(h) if self.check == "month" else week_end(h)):
            return None
        w = np.zeros(len(h.symbols))
        for i in h.panel.idx(FABER5):
            c = h.c[i]
            c = c[np.isfinite(c)]
            if self.signal == "sma200":
                on = len(c) >= 200 and c[-1] > c[-200:].mean()
            else:
                on = len(c) >= 253 and c[-1] / c[-253] - 1 > 0
            w[i] = 0.2 if on else 0.0
        return w


class LowVol:
    """E2: at each month end hold the N stocks (of the 100, no ETFs) with the lowest volatility of daily returns over
    the last L days, equal weight. Needs L+1 valid closes."""
    kind = "selection"

    def __init__(self, N=20, L=60):
        self.N, self.L = N, L
        self.name = f"lowvol_n{N}_l{L}"

    def _eligible_vol(self, h):
        out = {}
        for i in range(len(h.symbols)):
            if h.panel.etf[i]:
                continue
            c = h.c[i, -(self.L + 1):]
            if len(c) == self.L + 1 and np.all(np.isfinite(c)):
                out[i] = np.std(np.diff(np.log(c)))
        return out

    def weights(self, h):
        if not month_end(h):
            return None
        vol = self._eligible_vol(h)
        w = np.zeros(len(h.symbols))
        pick = sorted(vol, key=lambda i: (vol[i], h.symbols[i]))[:self.N]
        if len(pick) == self.N:
            w[pick] = 1.0 / self.N
        return w

    def random_weights(self, h, rng):
        if not month_end(h):
            return None
        pool = sorted(self._eligible_vol(h))
        w = np.zeros(len(h.symbols))
        if len(pool) >= self.N:
            w[rng.choice(pool, self.N, replace=False)] = 1.0 / self.N
        return w


class WeeklyReversal:
    """E3: at each week's last close buy the N stocks (of the 100) with the lowest return over the last L days,
    equal weight, hold until the next week's last close."""
    kind = "selection"

    def __init__(self, N=10, L=5):
        self.N, self.L = N, L
        self.name = f"weekrev_n{N}_l{L}"

    def _eligible_ret(self, h):
        out = {}
        for i in range(len(h.symbols)):
            if h.panel.etf[i] or h.c.shape[1] < self.L + 1:
                continue
            a, b = h.c[i, -(self.L + 1)], h.c[i, -1]
            if np.isfinite(a) and np.isfinite(b) and a > 0:
                out[i] = b / a - 1
        return out

    def weights(self, h):
        if not week_end(h):
            return None
        r = self._eligible_ret(h)
        w = np.zeros(len(h.symbols))
        pick = sorted(r, key=lambda i: (r[i], h.symbols[i]))[:self.N]
        if len(pick) == self.N:
            w[pick] = 1.0 / self.N
        return w

    def random_weights(self, h, rng):
        if not week_end(h):
            return None
        pool = sorted(self._eligible_ret(h))
        w = np.zeros(len(h.symbols))
        if len(pool) >= self.N:
            w[rng.choice(pool, self.N, replace=False)] = 1.0 / self.N
        return w


class TurnOfMonth:
    """E4: hold SPY for the intervals [open d, open d+1] where day d is one of the last `before` trading days of a
    month or one of the first `after` trading days; cash otherwise. Decided at the close of d-1 from the calendar."""
    kind = "timing"

    def __init__(self, before=1, after=3, symbol="SPY"):
        self.before, self.after, self.symbol = before, after, symbol
        self.name = f"tom_m{before}_p{after}"

    def weights(self, h):
        k = h.t + 1
        if k >= len(h.calendar):
            return None
        first, last = trading_day_of_month(h, k)
        on = first <= self.after or -last <= self.before
        w = np.zeros(len(h.symbols))
        i = h.panel.idx([self.symbol])
        if i and on:
            w[i[0]] = 1.0
        return w


class TrendBTC:
    """B001 (idea from the TradingKit/Trader.dev library: 'BTC frozen baseline', an SMA trend filter): hold BTC while
    the daily close is above its N-day simple average, else cash. Checked every day."""
    kind = "timing"

    def __init__(self, N=50):
        self.N, self.name = N, f"btc_sma{N}"

    def weights(self, h):
        c = h.c[0]
        c = c[np.isfinite(c)]
        if len(c) < self.N:
            return np.zeros(len(h.symbols))
        return np.array([1.0 if c[-1] > c[-self.N:].mean() else 0.0])


class MomentumBTC:
    """B002 (idea from the library: 'S12 Multi-Lookback TSMOM'): count how many of the 20-, 60- and 120-day returns are
    positive; hold BTC when at least `need` of 3 are. If scaled, size = min(1, 40% / realised 30-day volatility)."""
    kind = "timing"

    def __init__(self, need=2, scaled=False):
        self.need, self.scaled = need, scaled
        self.name = f"btc_tsmom{need}of3" + ("_volscaled" if scaled else "")

    def weights(self, h):
        c = h.c[0]
        c = c[np.isfinite(c)]
        if len(c) < 121:
            return np.zeros(1)
        votes = sum(c[-1] / c[-1 - L] - 1 > 0 for L in (20, 60, 120))
        if votes < self.need:
            return np.zeros(1)
        if not self.scaled:
            return np.ones(1)
        vol = np.std(np.diff(np.log(c[-31:]))) * np.sqrt(365)
        return np.array([min(1.0, 0.40 / vol) if vol > 0 else 1.0])


class TurnOfMonthBTC:
    """B003 (idea from the library: 'L1 Turn-of-the-Month Long (crypto calendar effect)'): hold BTC for the days from
    `start` calendar days before the month's last day through calendar day `end` of the next month."""
    kind = "timing"

    def __init__(self, start=4, end=2):
        self.start, self.end = start, end
        self.name = f"btc_tom_m{start}_p{end}"

    def weights(self, h):
        import calendar
        import datetime
        n = h.next_date()
        if n is None:
            return None
        d = datetime.date.fromisoformat(n)                     # the day this decision holds for
        last = calendar.monthrange(d.year, d.month)[1]
        on = d.day <= self.end or d.day > last - self.start
        return np.array([1.0 if on else 0.0])


CARDS = {
    "E001": lambda: [TrendETF(s, c) for s in ("sma200", "ret12m") for c in ("month", "week")],
    "E002": lambda: [LowVol(N, L) for N in (10, 20) for L in (60, 250)],
    "E003": lambda: [WeeklyReversal(N, L) for N in (5, 10) for L in (5, 10)],
    "E004": lambda: [TurnOfMonth(b, a) for b, a in ((1, 3), (2, 3), (1, 4), (3, 3))],
    "B001": lambda: [TrendBTC(N) for N in (20, 50, 100, 200)],
    "B002": lambda: [MomentumBTC(n, s) for n in (2, 3) for s in (False, True)],
    "B003": lambda: [TurnOfMonthBTC(a, b) for a, b in ((4, 2), (2, 2), (4, 4), (6, 2))],
}

BENCHMARKS = {"E001": lambda: Benchmark(FABER5, "Faber-5 ETFs equal weight"),
              "E002": lambda: Benchmark(None, "all 100 stocks equal weight"),
              "E003": lambda: Benchmark(None, "all 100 stocks equal weight"),
              "E004": lambda: Benchmark(["SPY"], "SPY buy and hold"),
              "B001": lambda: Benchmark(["BTC/USD"], "BTC buy and hold"),
              "B002": lambda: Benchmark(["BTC/USD"], "BTC buy and hold"),
              "B003": lambda: Benchmark(["BTC/USD"], "BTC buy and hold")}
