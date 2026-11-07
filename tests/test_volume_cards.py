"""H004 (gap-and-go) and H005 (volume spike): volume features, no look-ahead, stop levels, one entry per day."""
import numpy as np
import pytest

from stocks import features as F
from stocks.engine import run, simulate_trade, random_picker
from stocks.strategies import GapGo, VolSpike
from tests.test_stocks import FakeU


class VolU(FakeU):
    def __init__(self, S=20, D=40, seed=0):
        super().__init__(S, D, seed)
        rng = np.random.default_rng(seed + 100)
        self.bars[..., 4] = rng.lognormal(10, 0.8, size=self.bars.shape[:3]).astype(np.float32)


def feats(u):
    return {"prev_close": F.prev_close(u), "sigma60": F.sigma60(u),
            "open_vol_base": F.open_vol_base(u), "slot_vol_base": F.slot_vol_base(u)}


def test_volume_bases_use_prior_sessions_only():
    u = VolU(S=4, D=30)
    f = feats(u)
    s, d = 2, 25
    want_open = u.bars[s, d - 20:d, :6, 4].astype(float).sum(axis=1).mean()
    assert f["open_vol_base"][s, d] == pytest.approx(want_open, rel=1e-5)
    np.testing.assert_allclose(f["slot_vol_base"][s, d], u.bars[s, d - 20:d, :, 4].astype(float).mean(axis=0), rtol=1e-5)
    assert np.isnan(f["open_vol_base"][s, 19]) and np.isfinite(f["open_vol_base"][s, 20])
    u.bars[:, 25:, :, 4] *= 9                      # today and the future must not change today's base
    g = feats(u)
    np.testing.assert_allclose(f["open_vol_base"][:, :26], g["open_vol_base"][:, :26])
    np.testing.assert_allclose(f["slot_vol_base"][:, :26], g["slot_vol_base"][:, :26])


def test_invalid_days_are_skipped_in_bases():
    u = VolU(S=2, D=40)
    u.valid[0, 10] = False
    u.bars[0, 10, :, 4] = 1e12                     # a bad day's volume must not leak in
    f = feats(u)
    assert np.isnan(f["open_vol_base"][0, 10])
    assert f["open_vol_base"][0, 30] < 1e8


@pytest.mark.parametrize("st", [GapGo(G=-1.0, R=0.0), GapGo(G=0.0, R=0.5), VolSpike(R=0.5, H=6), VolSpike(R=1.5, H=12)])
def test_decisions_ignore_later_bars_same_day(st):
    """Scramble every bar after the decision bar (prices and volume): picks and stop levels must not change."""
    u = VolU(S=20, D=40, seed=5)
    fe = feats(u)
    d, total = 35, 0
    for slot in st.decision_slots:
        ctx = {k: v[:, d] for k, v in fe.items()}
        ctx.update({"bars": u.bars[:, d].copy(), "valid": u.valid[:, d].copy(), "entered": set()})
        before = st.select(ctx, slot, set())
        total += len(before)
        ctx["bars"][:, slot + 1:] *= np.random.default_rng(1).uniform(0.5, 1.5, size=ctx["bars"][:, slot + 1:].shape)
        assert st.select(ctx, slot, set()) == before
    assert total > 0


def test_gapgo_known_day():
    u = VolU(S=3, D=30, seed=2)
    fe = feats(u)
    d = 25
    pc = fe["prev_close"][0, d]
    day = u.bars[0, d]
    day[:, :4] = pc * 1.03                         # gaps +3% and sits flat
    day[:6, 1] = pc * 1.035                        # opening-range high
    day[:6, 2] = pc * 1.02                         # opening-range low (the stop)
    day[:6, 4] = fe["open_vol_base"][0, d] / 6 * 4  # 4x opening volume
    day[6, 3] = day[6, 1] = pc * 1.04              # 10:05 bar closes above the range high
    day[20, 2] = pc * 1.01                         # later low pierces the stop
    ctx = {k: v[:, d] for k, v in fe.items()}
    ctx.update({"bars": u.bars[:, d], "valid": u.valid[:, d].copy(), "entered": set()})
    picks = GapGo(G=0.02, R=3.0).select(ctx, 6, set())
    assert picks and picks[0][0] == 0 and picks[0][2] == 77 - 7
    assert picks[0][3] == pytest.approx(pc * 1.02, rel=1e-6)
    t = simulate_trade(ctx["bars"], 0, 7, 77, None, 0.0, picks[0][3])
    assert t["reason"] == "stop" and t["exit_slot"] == 20 and t["exit"] == pytest.approx(pc * 1.02, rel=1e-6)
    assert not GapGo(G=0.04, R=3.0).select(ctx, 6, set())      # gap too small
    assert not GapGo(G=0.02, R=5.0).select(ctx, 6, set())      # volume too small


@pytest.mark.parametrize("st", [GapGo(G=-1.0, R=0.0, K=3), VolSpike(R=0.8, H=6, K=3)])
def test_one_entry_per_stock_per_day_and_capacity(st):
    u = VolU(S=12, D=40, seed=7)
    _, trades = run(u, feats(u), st, "2017-01-25", "2017-02-28", cost=0.0)
    assert len(trades) > 10
    for d in {t["date"] for t in trades}:
        day = [t for t in trades if t["date"] == d]
        syms = [t["sym"] for t in day]
        assert len(syms) == len(set(syms))
        for s in range(78):
            assert sum(t["entry_slot"] <= s < t["exit_slot"] for t in day) <= st.K


def test_stop_level_semantics():
    day = np.zeros((1, 78, 5), dtype=np.float32)
    day[0, :, :] = [100, 101, 99.5, 100, 1]
    t = simulate_trade(day, 0, 10, 40, None, 0.0, 99.0)
    assert t["reason"] == "time"
    day[0, 12, 2] = 98.5
    t = simulate_trade(day, 0, 10, 40, None, 0.0, 99.0)
    assert (t["reason"], t["exit_slot"], round(t["exit"], 4)) == ("stop", 12, 99.0)
    day[0, 10, 0] = day[0, 10, 2] = 97.0           # entry bar opens below the level: out at that open
    t = simulate_trade(day, 0, 10, 40, None, 0.0, 99.0)
    assert (t["exit_slot"], round(t["exit"], 4), round(t["ret"], 6)) == (10, 97.0, 0.0)


@pytest.mark.parametrize("st", [GapGo(G=-1.0, R=0.0), VolSpike(R=0.8, H=6)])
def test_random_baseline_runs(st):
    u = VolU(S=12, D=40, seed=3)
    _, trades = run(u, feats(u), st, "2017-01-25", "2017-02-28", picker=random_picker(st, np.random.default_rng(0)))
    assert trades
