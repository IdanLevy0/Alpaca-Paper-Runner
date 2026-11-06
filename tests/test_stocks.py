"""Stock intraday engine: known-answer days, no look-ahead, and agreement with a slow bar-by-bar version."""
import numpy as np
import pytest

from stocks import features as F
from stocks.engine import run, simulate_trade, SealedHoldout
from stocks.strategies import Reversal, LateMomentum


class FakeU:
    def __init__(self, S=6, D=40, seed=0):
        rng = np.random.default_rng(seed)
        self.symbols = [f"S{i}" for i in range(S)]
        self.dates = np.array([f"2017-01-{k + 1:02d}" if k < 31 else f"2017-02-{k - 30:02d}" for k in range(D)])
        px = 100 * np.exp(np.cumsum(rng.normal(0, 0.003, size=(S, D * 78)), axis=1)).reshape(S, D, 78)
        o = np.concatenate([px[:, :, :1], px[:, :, :-1]], axis=2)
        hi = np.maximum(o, px) * (1 + np.abs(rng.normal(0, 0.001, size=px.shape)))
        lo = np.minimum(o, px) * (1 - np.abs(rng.normal(0, 0.001, size=px.shape)))
        self.bars = np.stack([o, hi, lo, px, np.ones_like(px)], axis=-1).astype(np.float32)
        self.valid = np.ones((S, D), dtype=bool)

    def day_range(self, a, b):
        return np.where((self.dates >= a) & (self.dates <= b))[0]


def feats(u):
    return {"prev_close": F.prev_close(u), "sigma60": F.sigma60(u)}


def test_trade_time_exit_and_stop():
    day = np.zeros((1, 78, 5), dtype=np.float32)
    day[0, :, :] = [100, 101, 99.5, 100, 1]
    t = simulate_trade(day, 0, 12, 24, 0.02, 0.0)
    assert (t["reason"], t["exit_slot"], round(t["ret"], 6)) == ("time", 24, 0.0)
    day[0, 15, 2] = 97.0                       # low pierces the 98 stop on slot 15
    t = simulate_trade(day, 0, 12, 24, 0.02, 0.0)
    assert (t["reason"], t["exit_slot"], round(t["exit"], 4)) == ("stop", 15, 98.0)
    day[0, 15, 0] = 96.0                       # opens below the stop -> exits at the open
    t = simulate_trade(day, 0, 12, 24, 0.02, 0.0)
    assert round(t["exit"], 4) == 96.0
    t = simulate_trade(day, 0, 12, 24, None, 0.001)
    assert t["ret"] == pytest.approx(0.999 / 1.001 - 1)


def test_features_do_not_peek():
    u = FakeU()
    f1 = feats(u)
    u.bars[:, 30:] *= 1.7                      # change the future
    f2 = feats(u)
    np.testing.assert_allclose(f1["sigma60"][:, :31], f2["sigma60"][:, :31])
    np.testing.assert_allclose(f1["prev_close"][:, :31], f2["prev_close"][:, :31])


def test_flat_by_close_and_capacity():
    u = FakeU(S=12, D=40, seed=4)
    for st in (Reversal(Z=0.5, H=24, K=3), LateMomentum(K=4)):
        daily, trades = run(u, feats(u), st, "2017-01-01", "2017-02-28", cost=0.0)
        assert trades and all(t["exit_slot"] <= 77 for t in trades)
        for d in {t["date"] for t in trades}:
            day = [t for t in trades if t["date"] == d]
            for s in range(78):
                assert sum(t["entry_slot"] <= s < t["exit_slot"] for t in day) <= st.K


def slow_reversal(u, fe, st, first, last):
    """Independent bar-by-bar version: walk every slot, exits first, then decisions at bar closes."""
    out = []
    for d in u.day_range(first, last):
        pos, done = [], []
        for s in range(78):
            for p in list(pos):
                o, l = u.bars[p["i"], d, s, 0], u.bars[p["i"], d, s, 2]
                if s == p["xs"]:
                    pos.remove(p); done.append((p["i"], p["es"], s, "time"))
                elif s >= p["es"] and p["stop"] is not None and (o <= p["stop"] or l <= p["stop"]):
                    pos.remove(p); done.append((p["i"], p["es"], s, "stop"))
            if s in st.decision_slots:
                ctx = {"bars": u.bars[:, d], "valid": u.valid[:, d].copy(), "sigma60": fe["sigma60"][:, d],
                       "prev_close": fe["prev_close"][:, d]}
                room = st.K - len(pos)
                for i, sf, h in st.select(ctx, s, {p["i"] for p in pos})[:max(0, room)]:
                    es = s + 1
                    pos.append({"i": i, "es": es, "xs": min(es + h, 77),
                                "stop": u.bars[i, d, es, 0] * (1 - sf) if sf else None})
        out += [(str(u.dates[d]),) + x for x in done]
    return sorted(out)


def test_engine_matches_slow_version():
    u = FakeU(S=15, D=40, seed=9)
    fe = feats(u)
    st = Reversal(Z=1.0, H=12, K=4)
    _, trades = run(u, fe, st, "2017-01-25", "2017-02-28", cost=0.0)
    fast = sorted((str(t["date"]), t["sym"], t["entry_slot"], t["exit_slot"], t["reason"]) for t in trades)
    slow = slow_reversal(u, fe, st, "2017-01-25", "2017-02-28")
    assert len(fast) > 20 and {r[4] for r in fast} == {"stop", "time"}
    assert fast == slow


def test_holdout_sealed():
    u = FakeU()
    u.dates = np.array([f"2024-01-{k + 1:02d}" for k in range(31)] + [f"2024-02-{k + 1:02d}" for k in range(9)])
    with pytest.raises(SealedHoldout):
        run(u, feats(u), Reversal(), "2024-01-01", "2024-02-09")


@pytest.mark.parametrize("st", [Reversal(Z=0.5, H=12, K=5), Reversal(Z=2.0, H=24), LateMomentum(K=5),
                                LateMomentum(K=10, market_filter=True)])
def test_decisions_ignore_later_bars_same_day(st):
    """The look-ahead test: scramble every bar AFTER the decision bar, picks must not change."""
    u = FakeU(S=20, D=40, seed=5)
    fe = feats(u)
    d = 35
    for slot in st.decision_slots:
        ctx = {"bars": u.bars[:, d].copy(), "valid": u.valid[:, d].copy(),
               "sigma60": fe["sigma60"][:, d], "prev_close": fe["prev_close"][:, d]}
        before = st.select(ctx, slot, set())
        ctx["bars"][:, slot + 1:] *= np.random.default_rng(1).uniform(0.5, 1.5, size=ctx["bars"][:, slot + 1:].shape)
        assert st.select(ctx, slot, set()) == before


def test_reversal_score_at_1030_uses_open():
    u = FakeU(S=3, D=30)
    fe = feats(u)
    ctx = {"bars": u.bars[:, 25], "valid": u.valid[:, 25], "sigma60": fe["sigma60"][:, 25], "prev_close": fe["prev_close"][:, 25]}
    z = Reversal().scores(ctx, 11)
    want = (u.bars[:, 25, 11, 3].astype(float) / u.bars[:, 25, 0, 0] - 1) / fe["sigma60"][:, 25]
    np.testing.assert_allclose(z, want)
