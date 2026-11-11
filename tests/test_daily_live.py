"""Daily runner: same targets as the backtest, once a day, sleeves only sell what they own, dry mode places nothing."""
from datetime import datetime, timezone

import numpy as np
import pytest

from daily import live as L
from daily.data import Panel
from daily.engine import decide
from daily.strategies import TrendETF, FABER5
from tests.test_daily import fake_panel


class FakeClient:
    def __init__(self, panel, today_idx, equity=100000.0):
        self.p, self.k, self.eq, self.orders = panel, today_idx, equity, []

    def clock(self):
        return {"is_open": True}

    def equity(self):
        return self.eq

    def daily_bars(self, syms, start, end):
        out = {}
        for s in syms:
            i = self.p.index[s]
            out[s] = [(self.p.dates[d], self.p.o[i, d], self.p.h[i, d], self.p.l[i, d], self.p.c[i, d], 1.0)
                      for d in range(self.k)]                       # only days before "today"
        return out

    def latest_prices(self, syms):
        return {s: float(self.p.o[self.p.index[s], self.k]) for s in syms}

    def buy_notional(self, *a):
        self.orders.append(("buy",) + a)
        return {"id": "x"}

    def sell_qty(self, *a):
        self.orders.append(("sell",) + a)
        return {"id": "x"}


SLEEVE = {"card": "E001", "variant": "trend_sma200_month", "stage": "learning", "vol": 0.08, "universe": FABER5}


def at(panel, k, hour=9, minute=40):
    from zoneinfo import ZoneInfo
    y, m, d = map(int, panel.dates[k].split("-"))
    return datetime(y, m, d, hour, minute, tzinfo=ZoneInfo("America/New_York")).astimezone(timezone.utc)


@pytest.fixture(autouse=True)
def tmp_state(tmp_path, monkeypatch):
    monkeypatch.setattr(L, "DIR", str(tmp_path))
    for name in ("TRADES_FILE", "VALUES_FILE", "RUNS_FILE", "STATE_FILE"):
        monkeypatch.setattr(L, name, str(tmp_path / name))


def test_targets_match_backtest():
    p = fake_panel(seed=4)
    k = 400
    fc = FakeClient(p, k)
    panel = L.build_panel(fc.daily_bars(FABER5, "", ""), p.dates[k])
    w, _ = L.targets(panel, SLEEVE)
    W, _ = decide(p, TrendETF("sma200", "month"), 0, k - 1)
    want = {p.symbols[i]: W[k - 1, i] for i in range(len(p.symbols)) if W[k - 1, i] > 0}
    assert w == pytest.approx(want)


def test_first_day_buys_then_waits_and_once_per_day():
    p = fake_panel(seed=4)
    k = 400
    fc = FakeClient(p, k)
    st = L.load_state()
    notes = L.step(fc, at(p, k), st, live=False, sleeves=[SLEEVE])
    held = st["sleeves"]["E001:trend_sma200_month"]["shares"]
    budget = 100000 * 0.05 * 1.0
    value = sum(q * fc.latest_prices([s])[s] for s, q in held.items())
    assert value <= budget + 1 and any("first day" in n for n in notes)
    assert L.step(fc, at(p, k, 10, 30), st, live=False, sleeves=[SLEEVE]) == []      # already done today
    assert fc.orders == []                                                          # dry mode: no orders


def test_before_935_does_nothing():
    p = fake_panel(seed=4)
    st = L.load_state()
    assert L.step(FakeClient(p, 400), at(p, 400, 9, 31), st, live=False, sleeves=[SLEEVE]) == []


def test_sleeve_never_sells_more_than_it_owns():
    p = fake_panel(seed=4)
    st = L.load_state()
    key = "E001:trend_sma200_month"
    st["sleeves"][key] = {"shares": {"SPY": 1.0, "QQQX": 0.0}, "invested": 100.0}
    k = next(k for k in range(380, 470) if p.dates[k][:7] != p.dates[k - 1][:7])   # first day of a month
    fc = FakeClient(p, k)
    L.step(fc, at(p, k), st, live=False, sleeves=[SLEEVE])
    assert all(q >= 0 for q in st["sleeves"][key]["shares"].values())


def test_live_orders_are_tagged_and_sells_go_first():
    p = fake_panel(seed=4)
    k = 400
    fc = FakeClient(p, k)
    fc.wait_filled = lambda oid: {"status": "filled", "filled_qty": 1.0, "filled_avg_price": 100.0}
    st = L.load_state()
    st["sleeves"]["E001:trend_sma200_month"] = {"shares": {"DBC": 50.0}, "invested": 1.0}
    L.step(fc, at(p, k), st, live=True, sleeves=[dict(SLEEVE)])
    kinds = [o[0] for o in fc.orders]
    assert kinds == sorted(kinds, key=lambda x: x != "sell")
    assert all(o[-1].startswith("d-E001-") for o in fc.orders)


class FakeCrypto:
    def __init__(self, n_days=200, start="2026-03-01"):
        import datetime as dt
        d0 = dt.date.fromisoformat(start)
        self.dates = [(d0 + dt.timedelta(days=k)).isoformat() for k in range(n_days)]
        self.orders = []

    def equity(self):
        return 100000.0

    def crypto_daily_bars(self, sym, start, end):
        return {sym: [(d, 100.0, 101.0, 99.0, 100.0, 1.0) for d in self.dates if d < end]}

    def crypto_price(self, sym):
        return 100.0


BTC_SLEEVE = {"card": "B003", "variant": "btc_tom_m4_p2", "stage": "learning", "vol": 0.278, "universe": ["BTC/USD"]}


def _utc(date, h=0, m=10):
    y, mo, d = map(int, date.split("-"))
    return datetime(y, mo, d, h, m, tzinfo=timezone.utc)


def test_crypto_sleeve_holds_only_around_month_end_and_once_a_day():
    fc = FakeCrypto()
    st = L.load_state()
    key = "B003:btc_tom_m4_p2"
    L.step_crypto(fc, _utc("2026-04-28"), st, False, [BTC_SLEEVE])     # 2 days before April's last day: in
    held = st["sleeves"][key]["shares"].get("BTC/USD", 0)
    assert held * 100 == pytest.approx(100000 * L.slice_pct(BTC_SLEEVE), rel=1e-6)
    assert L.step_crypto(fc, _utc("2026-04-28", 6), st, False, [BTC_SLEEVE]) == []   # once a day
    L.step_crypto(fc, _utc("2026-05-10"), st, False, [BTC_SLEEVE])     # mid-month: out
    assert st["sleeves"][key]["shares"].get("BTC/USD", 0) == 0
    assert L.step_crypto(fc, _utc("2026-05-11", 0, 2), st, False, [BTC_SLEEVE]) == []   # before 00:05


def test_btc_bot_ignores_sleeve_btc(tmp_path):
    import json
    f = tmp_path / "s.json"
    f.write_text(json.dumps({"sleeves": {"B003:x": {"shares": {"BTC/USD": 0.25}}, "E001:y": {"shares": {"SPY": 3}}}}))
    assert L.btc_held_by_sleeves(str(f)) == 0.25
    assert L.btc_held_by_sleeves(str(tmp_path / "missing.json")) == 0.0
