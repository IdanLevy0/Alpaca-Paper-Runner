"""The live stock bot must make the same trades as the backtest engine, minute by minute, with no peeking."""
from datetime import date, timedelta

import numpy as np
import pytest

from stockbot import live as L
from stocks import features as F
from stocks.engine import run
from stocks.strategies import Reversal


def weekdays(n, start=date(2017, 1, 3)):
    out, d = [], start
    while len(out) < n:
        if d.weekday() < 5:
            out.append(d.isoformat())
        d += timedelta(days=1)
    return out


class SynthU:
    def __init__(self, S=25, D=45, seed=3, vol=0.004):
        rng = np.random.default_rng(seed)
        self.symbols = [f"S{i:02d}" for i in range(S)]
        self.dates = np.array(weekdays(D))
        px = 100 * np.exp(np.cumsum(rng.normal(0, vol, size=(S, D * 78)), axis=1)).reshape(S, D, 78)
        jump = rng.random(size=px.shape) < 0.004                        # occasional sharp drops
        px = px * np.where(jump, 0.97, 1.0)
        o = np.concatenate([px[:, :, :1], px[:, :, :-1]], axis=2)
        hi = np.maximum(o, px) * (1 + np.abs(rng.normal(0, 0.0015, size=px.shape)))
        lo = np.minimum(o, px) * (1 - np.abs(rng.normal(0, 0.0015, size=px.shape)))
        self.bars = np.round(np.stack([o, hi, lo, px, np.full_like(px, 1000)], axis=-1), 2).astype(np.float32)
        self.valid = np.ones((S, D), dtype=bool)

    def day_range(self, a, b):
        return np.where((self.dates >= a) & (self.dates <= b))[0]


class FakeAlpaca:
    """Serves only finished bars; market orders fill at the open of the bar starting now; stops fill on lows."""

    def __init__(self, u):
        self.u, self.now, self.orders, self.n = u, None, {}, 0
        self.col = {d: k for k, d in enumerate(u.dates.tolist())}

    def _slot_now(self):
        d = self.now.astimezone(L.NY).date().isoformat()
        k = int((self.now - L.slot_start(d, 0)).total_seconds() // 300)
        return d, k

    def advance(self, now):
        self.now = now
        d, k = self._slot_now()
        day = self.col.get(d)
        for o in self.orders.values():
            if o["type"] == "stop" and o["status"] == "new":
                i = self.u.symbols.index(o["symbol"])
                for s in range(o["from_slot"], min(k, 78)):
                    b = self.u.bars[i, day, s]
                    if b[2] <= o["stop"]:
                        o.update(status="filled", filled_avg_price=str(min(o["stop"], float(b[0]))), filled_qty=str(o["qty"]))
                        break
                o["from_slot"] = max(o["from_slot"], min(k, 78))

    def clock(self):
        d, k = self._slot_now()
        return {"is_open": d in self.col and 0 <= k < 78}

    def calendar(self, start, end):
        return [{"date": d} for d in self.u.dates.tolist() if start <= d <= end]

    def equity(self):
        return 100000.0

    def bars(self, symbols, start, end, feed):
        out = {}
        for d in self.u.dates.tolist():
            for k in range(78):
                t0 = L.slot_start(d, k)
                if not (L.iso(t0) >= start and L.iso(t0) < end) or t0 + timedelta(minutes=5) > self.now:
                    continue
                for s in symbols:
                    o, h, l, c, v = (float(x) for x in self.u.bars[self.u.symbols.index(s), self.col[d], k])
                    out.setdefault(s, []).append({"t": L.iso(t0), "o": o, "h": h, "l": l, "c": c, "v": v})
        return out

    def _new(self, **o):
        self.n += 1
        o.update(id=f"o{self.n}")
        self.orders[o["id"]] = o
        return o

    def _fill_now(self, symbol):
        d, k = self._slot_now()
        return float(self.u.bars[self.u.symbols.index(symbol), self.col[d], k, 0])

    def buy(self, symbol, qty, coid):
        return self._new(type="market", symbol=symbol, status="filled", filled_avg_price=str(self._fill_now(symbol)), filled_qty=str(qty))

    def sell(self, symbol, qty, coid):
        return self._new(type="market", symbol=symbol, status="filled", filled_avg_price=str(self._fill_now(symbol)), filled_qty=str(qty))

    def stop(self, symbol, qty, stop_price, coid):
        return self._new(type="stop", symbol=symbol, status="new", stop=round(stop_price, 2), qty=qty, from_slot=self._slot_now()[1])

    def cancel(self, oid):
        if self.orders[oid]["status"] == "new":
            self.orders[oid]["status"] = "canceled"

    def order(self, oid):
        return self.orders[oid]

    def wait_filled(self, oid):
        return self.orders[oid]


@pytest.fixture
def isolated(tmp_path, monkeypatch):
    for name in ("STATE_FILE", "TRADES_FILE", "DAYS_FILE", "RUNS_FILE"):
        monkeypatch.setattr(L, name, str(tmp_path / name))
    monkeypatch.setattr(L, "STATE_DIR", str(tmp_path))
    return tmp_path


def replay(u, strat, days, live=True):
    fake, st, log = FakeAlpaca(u), L.load_state(), []
    for d in days:
        for k in range(78):
            now = L.slot_start(d, k)
            fake.advance(now)
            log += L.step(fake, now, st, live, strategy=strat, symbols=u.symbols)
    return fake, st, log


@pytest.mark.parametrize("seed,strat", [(3, Reversal(Z=1.5, H=12, K=4)), (11, Reversal(Z=2.0, H=24, K=5)),
                                        (12, Reversal(Z=1.0, H=24, K=3))])
def test_live_matches_engine(isolated, seed, strat):
    u = SynthU(seed=seed)
    days = u.dates.tolist()[30:]
    fe = {"prev_close": F.prev_close(u), "sigma60": F.sigma60(u)}
    _, eng = run(u, fe, strat, days[0], days[-1], cost=0.0)
    fake, st, log = replay(u, strat, days)
    import csv
    live = list(csv.DictReader(open(L.TRADES_FILE)))
    assert len(eng) >= 15, len(eng)
    assert {t["reason"] for t in eng} >= {"stop", "time"}
    a = sorted((str(t["date"]), u.symbols[t["sym"]], round(float(t["entry"]), 2), round(float(t["exit"]), 2),
                {"time": "time"}.get(t["reason"], t["reason"])) for t in eng)
    b = sorted((r["date"], r["symbol"], round(float(r["entry"]), 2), round(float(r["exit"]), 2),
                "time" if r["reason"] in ("time", "flat") else r["reason"]) for r in live)
    assert a == b


def test_dry_mode_sends_no_orders(isolated):
    u = SynthU(seed=5)
    fake, st, log = replay(u, Reversal(Z=1.5, H=12, K=4), u.dates.tolist()[30:33], live=False)
    assert not fake.orders
    assert any(n.startswith("ENTRY") for n in log)


def test_flat_by_close_and_summary(isolated):
    u = SynthU(seed=8)
    fake, st, log = replay(u, Reversal(Z=1.0, H=60, K=5), u.dates.tolist()[30:32])
    assert not st["positions"]
    assert any("flat" in n for n in log)
    assert sum(1 for _ in open(L.DAYS_FILE)) == 1 + 2      # header + one row per day


def test_late_pass_skips_decision(isolated):
    u = SynthU(seed=9)
    fake, st = FakeAlpaca(u), L.load_state()
    d = u.dates.tolist()[31]
    now = L.slot_start(d, 12) + timedelta(minutes=25)       # 25 min after the 10:30 decision
    fake.advance(now)
    notes = L.step(fake, now, st, True, strategy=Reversal(Z=0.5), symbols=u.symbols)
    assert any(n.startswith("MISSED") for n in notes) and not st["positions"]


def test_features_match_research_code():
    u = SynthU(seed=4)
    fake = FakeAlpaca(u)
    d = u.dates.tolist()[35]
    fake.now = L.slot_start(d, 0)
    feats = L.morning_features(fake, u.symbols, d)
    k = u.dates.tolist().index(d)
    pc, sg = F.prev_close(u)[:, k], F.sigma60(u)[:, k]
    for i, s in enumerate(u.symbols):
        assert feats[s][0] == pytest.approx(pc[i]) and feats[s][1] == pytest.approx(sg[i], rel=1e-9)


def test_replay_matches_live_bot(isolated, monkeypatch):
    """The replay page's trades must be the live bot's trades on the same data."""
    import csv
    from stockbot import replay as R, config as C
    u = SynthU(seed=11)
    strat = Reversal(Z=2.0, H=24, K=5)
    monkeypatch.setattr(C, "SYMBOLS", u.symbols)
    monkeypatch.setattr(C, "STRATEGY", strat)
    fake = FakeAlpaca(u)
    end = L.slot_start(u.dates.tolist()[-1], 78) + timedelta(hours=2)
    fake.now = end
    data = R.build(fake, 10, end)
    replay(u, strat, u.dates.tolist()[-10:])
    live = sorted((r["date"], r["symbol"], round(float(r["entry"]), 2), round(float(r["exit"]), 2)) for r in csv.DictReader(open(L.TRADES_FILE)))
    rep = sorted((t["date"], t["symbol"], t["entry"], t["exit"]) for t in data["trades"])
    assert len(rep) >= 5 and rep == live
    assert all(t["z"] <= -2.0 and len(t["bars"]) == 78 for t in data["trades"])
