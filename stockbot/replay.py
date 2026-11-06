"""Replay the last N trading days with REAL Alpaca data through the bot's rules, no orders.

python -m stockbot.replay [DAYS]  ->  state/stocks/replay.json (for the replay page)
- Features (prev close, sigma60) from full-market SIP bars of the prior sessions, as each morning live.
- Intraday bars from IEX, the free real-time feed the live bot sees.
- Trades simulated with the backtest engine (stocks/engine.py), which the live bot matches trade for trade
  (tests/test_stockbot.py). Shown before costs and after 0.03% per side.
This uses the sealed holdout period (2024 on) for H001 ONLY, at Idan's request (H001 already failed and is frozen).
"""
import json
import os
import sys
from datetime import datetime, timedelta, timezone

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from stockbot import config as C                                         # noqa: E402
from stockbot.live import History, slot_start, iso, NY, STATE_DIR, safe_error  # noqa: E402
from stocks import features as F                                         # noqa: E402
from stocks.engine import run, COST                                      # noqa: E402


def build(client, days, now):
    cal = client.calendar((now - timedelta(days=120)).date().isoformat(), now.date().isoformat())
    done = [c["date"] for c in cal if slot_start(c["date"], 78) + timedelta(minutes=20) <= now]
    replay_days = done[-days:]
    all_days = done[-(days + C.HISTORY_DAYS + 3):]
    sip = History(C.SYMBOLS, all_days,
                  client.bars(C.SYMBOLS, iso(slot_start(all_days[0], 0)), iso(slot_start(all_days[-1], 78)), feed="sip"))
    feats = {"prev_close": F.prev_close(sip), "sigma60": F.sigma60(sip)}
    iex = History(C.SYMBOLS, all_days,
                  client.bars(C.SYMBOLS, iso(slot_start(replay_days[0], 0)), iso(slot_start(replay_days[-1], 78)), feed="iex"))
    st = C.STRATEGY
    first, last = replay_days[0], replay_days[-1]
    daily0, trades0 = run(iex, feats, st, first, last, cost=0.0, allow_holdout=True)
    daily, trades = run(iex, feats, st, first, last, cost=COST, allow_holdout=True)
    col = {d: k for k, d in enumerate(all_days)}
    out_trades = []
    for t0, t in zip(trades0, trades):
        d, i = str(t["date"]), int(t["sym"])
        k, ds = col[d], t["entry_slot"] - 1
        bars = iex.bars[i, k]
        sig = float(feats["sigma60"][i, k])
        ref = float(bars[ds - 12, 3]) if ds >= 12 else float(bars[0, 0])
        r60 = float(bars[ds, 3]) / ref - 1
        out_trades.append({
            "date": d, "symbol": C.SYMBOLS[i], "decision": slot_start(d, ds + 1).astimezone(NY).strftime("%H:%M"),
            "entry_time": slot_start(d, t["entry_slot"]).astimezone(NY).strftime("%H:%M"),
            "exit_time": slot_start(d, t["exit_slot"]).astimezone(NY).strftime("%H:%M"),
            "entry_slot": t["entry_slot"], "exit_slot": t["exit_slot"], "decision_slot": ds,
            "entry": round(float(t["entry"]), 2), "exit": round(float(t["exit"]), 2), "reason": t["reason"],
            "ret_gross_pct": round(t0["ret"] * 100, 3), "ret_net_pct": round(t["ret"] * 100, 3),
            "drop60_pct": round(r60 * 100, 2), "sigma60_pct": round(sig * 100, 3), "z": round(r60 / sig, 2),
            "stop": round(float(t["entry"]) * (1 - 2 * sig), 2), "prev_close": round(float(feats["prev_close"][i, k]), 2),
            "bars": [[round(float(x), 2) for x in b[:4]] for b in bars]})
    days_out = []
    for (d, r0, n), (_, r, _) in zip(daily0, daily):
        k = col[d]
        ok = iex.valid[:, k]
        mkt = float(np.nanmean(np.where(ok, iex.bars[:, k, 77, 3] / np.where(ok, iex.bars[:, k, 0, 0], np.nan) - 1, np.nan)))
        days_out.append({"date": d, "trades": n, "ret_gross_pct": round(r0 * 100, 3), "ret_net_pct": round(r * 100, 3),
                         "market_intraday_pct": round(mkt * 100, 3)})
    return {"generated": iso(now), "strategy": st.name, "label": C.LABEL, "K": st.K, "Z": getattr(st, "Z", None),
            "H": getattr(st, "H", None), "cost_pct_per_side": COST * 100, "first": first, "last": last,
            "days": days_out, "trades": out_trades,
            "decision_times": [slot_start(first, s + 1).astimezone(NY).strftime("%H:%M") for s in st.decision_slots]}


def main(days=21):
    from stockbot.client import StockClient
    data = build(StockClient.from_env(), days, datetime.now(timezone.utc))
    os.makedirs(STATE_DIR, exist_ok=True)
    with open(os.path.join(STATE_DIR, "replay.json"), "w") as f:
        json.dump(data, f, separators=(",", ":"))
    n = len(data["trades"])
    net = np.prod([1 + d["ret_net_pct"] / 100 for d in data["days"]]) - 1
    print(f"{data['first']} to {data['last']}: {n} trades, {net * 100:+.2f}% after costs")


if __name__ == "__main__":
    try:
        main(int(sys.argv[1]) if len(sys.argv) > 1 else 21)
    except Exception as e:
        print(safe_error(e))
        sys.exit(1)
