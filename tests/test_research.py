import json
import random

import pytest

from backtest import engine
from research import run_research as RR
from research.fast import breakout_trades
from research.stats import bootstrap_pvalue
from runner.strategies import make_breakout_trend
from tests.test_parity import make_bars

SETTINGS = [{}, {"lookback": 10, "stop_atr": 1.5, "trail_atr": 2.0, "exit_ema": 20},
            {"lookback": 55, "stop_atr": 3.0, "trail_atr": 5.0, "exit_ema": 100}]


@pytest.mark.parametrize("p", SETTINGS)
def test_fast_matches_engine(p):
    bars = make_bars(3000, seed=21)
    sig, mgr = make_breakout_trend(**p)
    slow = engine.run(bars, sig, manager=mgr)
    fast = breakout_trades(bars, **p)
    assert len(slow) > 10
    assert [(t["entry_time"], t["exit_time"], t["reason"]) for t in slow] == \
           [(t["entry_time"], t["exit_time"], t["reason"]) for t in fast]
    for a, b in zip(slow, fast):
        assert a["ret"] == pytest.approx(b["ret"], abs=1e-9)


def test_bootstrap_sane():
    rnd = random.Random(1)
    good = [0.02 + rnd.gauss(0, 0.03) for _ in range(150)]
    noise = [rnd.gauss(0, 0.03) for _ in range(150)]
    m = sum(noise) / len(noise)
    noise = [x - m for x in noise]          # exactly zero average: should look like pure chance
    assert bootstrap_pvalue(good, n_boot=1000)["p"] < 0.01
    assert 0.3 < bootstrap_pvalue(noise, n_boot=1000)["p"] < 0.7


def test_report_and_replay_build(tmp_path, monkeypatch):
    monkeypatch.setattr(RR, "ROOT", str(tmp_path))
    (tmp_path / "research").mkdir()
    import shutil, os
    shutil.copy(os.path.join(os.path.dirname(RR.__file__), "replay_template.html"), tmp_path / "research")
    monkeypatch.setitem(RR.GRID, "lookback", [10, 20])
    monkeypatch.setitem(RR.GRID, "trail_atr", [3.0, 4.0])
    bars = {s: make_bars(9000, seed=k) for k, s in enumerate(RR.SYMBOLS)}
    import tests.test_parity as tp
    start = "2021-01-01T00:00:00Z"
    from datetime import datetime, timedelta, timezone
    t0 = datetime(2020, 6, 1, tzinfo=timezone.utc)
    for s in bars:
        for k, b in enumerate(bars[s]):
            b["t"] = (t0 + timedelta(hours=4 * k)).strftime("%Y-%m-%dT%H:%M:%SZ")
    RR.main(lambda s: bars[s])
    text = (tmp_path / "RESEARCH_REPORT.md").read_text()
    assert "## BTC/USD" in text and "Luck p-value" in text
    html = (tmp_path / "research" / "out" / "replay.html").read_text()
    assert "/*__DATA__*/null" not in html
    data = json.loads(html.split("const DATA = ", 1)[1].split(";\n", 1)[0])
    assert set(data["coins"]) == set(RR.SYMBOLS)
