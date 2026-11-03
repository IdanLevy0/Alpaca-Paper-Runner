"""Dry mode and the kill switch must never send an order."""
import os
from datetime import timedelta

from runner import run as R
from tests.test_parity import FakeAlpaca, make_bars, isolated  # noqa: F401
from runner.strategies import LOOKBACK


class NoOrders(FakeAlpaca):
    def _new(self, **o):
        raise AssertionError("an order was sent")


def test_dry_mode_sends_nothing(isolated):
    bars = make_bars(LOOKBACK + 200)
    fake, st, entries = NoOrders(bars), {"in_trade": False, "last_signal_bar": None, "entries": {}}, 0
    for k in range(len(bars)):
        fake.advance(k)
        notes = R.step(fake, fake.now(), st, live=False)
        entries += sum(n.startswith("ENTRY") for n in notes)
    assert entries > 5   # decisions still happen and get logged


def test_kill_file_forces_dry(isolated, monkeypatch):
    monkeypatch.setenv("TRADING_ENABLED", "true")
    monkeypatch.setattr(R, "KILL_FILE", str(isolated / "KILL"))
    open(R.KILL_FILE, "w").close()
    assert R.trading_live() is False
    os.remove(R.KILL_FILE)
    assert R.trading_live() is True


def test_same_candle_checked_once(isolated):
    bars = make_bars(LOOKBACK + 50)
    fake, st = FakeAlpaca(bars), {"in_trade": False, "last_signal_bar": None, "entries": {}}
    fake.advance(len(bars) - 1)
    R.step(fake, fake.now(), st, live=False)
    if not st["in_trade"]:
        notes = R.step(fake, fake.now() + timedelta(minutes=5), st, live=False)
        assert "already checked" in notes[0]
