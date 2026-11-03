"""The live runner and the backtest engine must make the same trades on the same candles."""
import random
from datetime import datetime, timedelta, timezone

import pytest

from backtest import engine
from runner import config, run as R
from runner.strategies import STRATEGIES, LOOKBACK

H4 = timedelta(hours=4)
T0 = datetime(2024, 1, 1, tzinfo=timezone.utc)


def make_bars(n, seed=1):
    random.seed(seed)
    bars, px = [], 40000.0
    for k in range(n):
        o = px
        c = o * (1 + random.gauss(0.0004, 0.012))
        h = max(o, c) * (1 + abs(random.gauss(0, 0.006)))
        l = min(o, c) * (1 - abs(random.gauss(0, 0.006)))
        bars.append({"t": R.iso(T0 + k * H4), "o": o, "h": h, "l": l, "c": c, "v": 1.0})
        px = c  # next open = this close, so "next open" and "fill now" are the same price
    return bars


def frequent(bars):
    """Test-only strategy that fires often: two up closes in a row."""
    if len(bars) < 3 or not (bars[-1]["c"] > bars[-2]["c"] > bars[-3]["c"]):
        return None
    return {"stop_dist": bars[-1]["c"] * 0.02, "target_dist": bars[-1]["c"] * 0.03, "max_bars": 6}


class FakeAlpaca:
    """Replays candles. Market orders fill at the last close; the exchange stop fills during a candle."""

    def __init__(self, bars):
        self.all, self.k, self.pos, self.orders, self.n = bars, -1, 0.0, {}, 0

    def advance(self, k):
        self.k, b = k, self.all[k]
        for o in self.orders.values():
            if o["type"] == "stop" and o["status"] == "open" and b["l"] <= o["stop"]:
                o.update(status="filled", filled_avg_price=str(min(o["stop"], b["o"])), filled_qty=str(o["qty"]))
                self.pos -= o["qty"]

    def now(self):
        return T0 + (self.k + 1) * H4

    def bars(self, sym, tf, start):
        vis = self.all[:self.k + 1]
        return [b for b in vis if b["t"] >= start] if tf == "4Hour" else [b for b in vis if b["t"] >= R.iso(R.ts(start) - H4)][-1:]

    def position_qty(self, sym): return self.pos
    def equity(self): return 100000.0
    def order(self, oid): return self.orders[oid]
    def cancel(self, oid): self.orders[oid]["status"] = "canceled"

    def _new(self, **o):
        self.n += 1
        o["id"] = f"o{self.n}"
        self.orders[o["id"]] = o
        return o

    def buy_notional(self, sym, notional, coid):
        px = self.all[self.k]["c"]
        self.pos += notional / px
        return self._new(type="market", status="filled", filled_avg_price=str(px), filled_qty=str(notional / px))

    def sell_market(self, sym, qty, coid):
        self.pos -= qty
        return self._new(type="market", status="filled", filled_avg_price=str(self.all[self.k]["c"]), filled_qty=str(qty))

    def sell_stop(self, sym, qty, stop, coid):
        return self._new(type="stop", status="open", stop=stop, qty=qty)

    def wait_filled(self, oid): return self.orders[oid]


@pytest.fixture
def isolated(tmp_path, monkeypatch):
    for name in ("STATE_FILE", "TRADES_FILE", "RUNS_FILE"):
        monkeypatch.setattr(R, name, str(tmp_path / name))
    monkeypatch.setattr(R, "STATE_DIR", str(tmp_path))
    monkeypatch.setitem(STRATEGIES, "frequent", frequent)
    monkeypatch.setattr(config, "STRATEGY", "frequent")
    monkeypatch.setattr(config, "MAX_ENTRIES_PER_DAY", 99)
    return tmp_path


def replay(bars):
    fake, st, trades = FakeAlpaca(bars), {"in_trade": False, "last_signal_bar": None, "entries": {}}, []
    for k in range(len(bars)):
        fake.advance(k)
        was = st["in_trade"]
        snap = dict(st)
        notes = R.step(fake, fake.now(), st, live=True)
        if was and not st["in_trade"]:
            reason = next(n.split()[1] for n in notes if n.startswith("EXIT"))
            trades.append({"entry_bar": snap["entry_bar_t"], "exit_bar": bars[k]["t"], "reason": reason,
                           "entry": snap["entry"]})
    return trades


def test_live_runner_matches_backtest(isolated):
    bars = make_bars(LOOKBACK + 400)
    bt = engine.run(bars, frequent, fee=0, slippage=0)
    live = replay(bars)
    assert len(bt) > 20
    # the engine skips a trade still open at the end of data; compare the closed ones
    assert len(live) == len(bt)
    for a, b in zip(bt, live):
        assert a["entry_time"] == b["entry_bar"]
        assert a["exit_time"] == b["exit_bar"]
        assert a["reason"] == b["reason"]
        assert a["entry"] == pytest.approx(b["entry"])


@pytest.mark.parametrize("name", ["trend_pullback", "donchian_breakout", "thrust_long"])
def test_real_strategies_run(name):
    bars = make_bars(LOOKBACK + 600, seed=7)
    trades = engine.run(bars, STRATEGIES[name])
    for t in trades:
        assert t["reason"] in ("stop", "target", "time")
