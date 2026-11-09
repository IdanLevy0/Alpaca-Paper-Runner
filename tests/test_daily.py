"""Multi-day engine and strategies: known answers, costs, no look-ahead, sealed holdout, baselines."""
import datetime

import numpy as np
import pytest

from daily.data import Panel, History
from daily.engine import decide, simulate, shifted, SealedHoldout, stats
from daily.strategies import (TrendETF, LowVol, WeeklyReversal, TurnOfMonth, Benchmark, FABER5, month_end, week_end,
                              CARDS)


def trading_days(start="2016-01-04", n=600):
    d, out = datetime.date.fromisoformat(start), []
    while len(out) < n:
        if d.weekday() < 5:
            out.append(d.isoformat())
        d += datetime.timedelta(days=1)
    return out


def fake_panel(n_stocks=30, n_days=600, seed=0):
    rng = np.random.default_rng(seed)
    syms = FABER5 + ["SPY2"] + [f"S{i:02d}" for i in range(n_stocks)]
    N = len(syms)
    vol = np.concatenate([np.full(6, 0.008), np.linspace(0.005, 0.03, n_stocks)])
    c = 100 * np.exp(np.cumsum(rng.normal(0.0003, 1, size=(N, n_days)) * vol[:, None], axis=1))
    o = c * np.exp(rng.normal(0, 0.002, size=c.shape))
    etf = np.array([True] * 6 + [False] * n_stocks)
    return Panel(syms, trading_days(n=n_days), o, np.maximum(o, c), np.minimum(o, c), c, np.ones_like(c), etf)


def test_known_answer_and_costs():
    p = fake_panel(n_stocks=2, n_days=30)
    p.o[:] = 100.0
    p.o[0, 10:] = 110.0                       # SPY's open jumps 10% on day 10
    W, R = np.zeros((30, len(p.symbols))), np.zeros(30, dtype=bool)
    W[5:, 0], R[5] = 1.0, True                # decided at close of day 5 -> bought at the open of day 6
    d, r, _ = simulate(p, W, R, p.dates[6], p.dates[20], 0.0)
    assert d[0] == p.dates[6] and np.prod(1 + r) == pytest.approx(1.10)
    assert r[3] == pytest.approx(0.10)        # interval [open 9, open 10]
    d, r, _ = simulate(p, W, R, p.dates[6], p.dates[20], 0.001)
    assert np.prod(1 + r) == pytest.approx(1.10 - 0.001)      # 0.1% paid once on $1 bought


def test_window_starts_invested_and_ends_inside_period():
    p = fake_panel(n_stocks=2, n_days=60)
    W, R = np.zeros((60, len(p.symbols))), np.zeros(60, dtype=bool)
    W[:, 0], R[0] = 1.0, True
    d, r, _ = simulate(p, W, R, p.dates[30], p.dates[40], 0.0)
    assert len(d) == 10 and d[-1] == p.dates[39]          # last interval ends at the open of day 40
    want = p.o[0, 40] / p.o[0, 30]
    assert np.prod(1 + r) == pytest.approx(want)


def test_holdout_sealed():
    p = fake_panel(n_stocks=2, n_days=40)
    W, R = np.zeros((40, len(p.symbols))), np.zeros(40, dtype=bool)
    with pytest.raises(SealedHoldout):
        simulate(p, W, R, p.dates[0], p.dates[39], 0.0, holdout_start=p.dates[20])


ALL = [s for c in CARDS.values() for s in c()] + [Benchmark(FABER5), Benchmark(None)]


@pytest.mark.parametrize("st", ALL, ids=lambda s: s.name)
def test_no_look_ahead(st):
    """Scramble every price after day t: the decision at the close of t must not change."""
    p = fake_panel(seed=3)
    for t in (300, 301, 302, 303, 304, 330, 351, 420, 455, 520):
        a = st.weights(History(p, t))
        q = fake_panel(seed=3)
        rng = np.random.default_rng(t)
        for arr in (q.o, q.h, q.l, q.c):
            arr[:, t + 1:] *= rng.uniform(0.5, 1.5, size=arr[:, t + 1:].shape)
        b = st.weights(History(q, t))
        assert (a is None and b is None) or np.allclose(a, b)


def test_history_has_no_future_prices():
    p = fake_panel()
    h = History(p, 100)
    assert h.c.shape[1] == 101 and h.o.shape[1] == 101


def test_calendar_helpers():
    p = fake_panel(n_days=80)
    ends = [p.dates[t] for t in range(79) if month_end(History(p, t))]
    assert ends[:2] == ["2016-01-29", "2016-02-29"]
    wk = [p.dates[t] for t in range(10) if week_end(History(p, t))]
    assert wk[:2] == ["2016-01-08", "2016-01-15"]


def test_turn_of_month_days():
    p = fake_panel(n_days=80)
    st = TurnOfMonth(1, 3, symbol="SPY")
    W, R = decide(p, st, 0, 78)
    held = [p.dates[t + 1] for t in range(78) if W[t, 0] == 1.0]
    assert "2016-01-29" in held and "2016-02-01" in held and "2016-02-03" in held
    assert "2016-02-04" not in held and "2016-01-28" not in held
    assert len([d for d in held if d[:7] == "2016-02"]) == 4    # first 3 of Feb + last of Feb


def test_low_vol_picks_calmest_and_reversal_picks_losers():
    p = fake_panel(seed=5)
    t = next(t for t in range(300, 400) if month_end(History(p, t)))
    w = LowVol(N=5, L=60).weights(History(p, t))
    picked = sorted(np.where(w > 0)[0])
    assert all(not p.etf[i] for i in picked) and w.sum() == pytest.approx(1.0)
    assert max(picked) < 6 + 12                               # the low-vol end of the synthetic stocks
    t = next(t for t in range(300, 400) if week_end(History(p, t)))
    w = WeeklyReversal(N=5, L=5).weights(History(p, t))
    r = p.c[:, t] / p.c[:, t - 5] - 1
    stocks = [i for i in range(len(p.symbols)) if not p.etf[i]]
    assert set(np.where(w > 0)[0]) == set(sorted(stocks, key=lambda i: r[i])[:5])


def test_trend_uses_only_faber_five():
    p = fake_panel(seed=2)
    t = next(t for t in range(300, 400) if month_end(History(p, t)))
    w = TrendETF().weights(History(p, t))
    assert set(np.where(w > 0)[0]) <= set(p.idx(FABER5)) and w.sum() <= 1.0 + 1e-12


def test_shifted_keeps_exposure():
    p = fake_panel(n_days=300)
    W, R = decide(p, TurnOfMonth(1, 3, symbol="SPY"), 0, 298)
    W2, R2 = shifted(W, R, 50, 250, 37)
    assert W2[50:251, 0].sum() == W[50:251, 0].sum() and not np.array_equal(W2, W)


def test_long_only_no_leverage_enforced():
    class Bad:
        def weights(self, h):
            w = np.zeros(len(h.symbols)); w[:2] = 0.8
            return w
    with pytest.raises(AssertionError):
        decide(fake_panel(n_days=30), Bad(), 0, 10)


def test_stats_basic():
    s = stats(np.full(252, 0.001))
    assert s["cagr_pct"] == pytest.approx((1.001 ** 252 - 1) * 100) and s["max_dd_pct"] == 0


def test_research_runs_end_to_end_on_fake_data(monkeypatch):
    from daily import research as RS
    p = fake_panel(n_stocks=30, n_days=2100, seed=8)       # 2016-01 .. 2024-01
    res, bench, bname, periods = RS.run_card("E002", n_random=5, panel=p)
    text, g1, g2 = RS.report("E002", res, bench, bname, periods)
    assert "Gate 1" in text and "(best)" in text
    q = fake_panel(n_stocks=0, n_days=2100, seed=9)
    q = Panel(["BTC/USD"], [d for d in trading_days(n=2100)], q.o[:1], q.h[:1], q.l[:1], q.c[:1], q.v[:1])
    res, bench, bname, periods = RS.run_card("B001", n_random=5, panel=q)
    text, _, _ = RS.report("B001", res, bench, bname, periods)
    assert "btc_sma" in text
