"""Stock paper bot: one pass. Runs every ~5 minutes from GitHub Actions (same workflow as the BTC bot).

Same rules as the backtest (stocks/engine.py) with the strategy object from stockbot/config.py:
- Each morning: fetch the prior HISTORY_DAYS sessions (sip feed, >15 min old so free) and compute sigma60 and the
  previous close with stocks/features.py, exactly as the research code does.
- At each decision bar close (10:30, 11:30, ...): build today's bars so far (iex feed, real time) and call
  strategy.select(). Buy whole shares at market right away (backtest: next bar's open), place a stop order on Alpaca.
- Time exit at the open of the exit bar; everything sold from 15:55; no trading on early-close days.
- Orders only when STOCKS_ENABLED=true and state/KILL does not exist; otherwise dry mode (decisions logged only).
Never touches BTC/USD or any order that does not start with ORDER_PREFIX.
"""
import csv
import json
import math
import os
import sys
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from stockbot import config as C                       # noqa: E402
from stocks import features as F                       # noqa: E402
from stocks.data import day_to_array, SLOTS, EARLY, MAX_WICK  # noqa: E402

NY = ZoneInfo("America/New_York")
STATE_DIR = os.path.join(ROOT, "state", "stocks")
STATE_FILE = os.path.join(STATE_DIR, "state.json")
TRADES_FILE = os.path.join(STATE_DIR, "trades.csv")
DAYS_FILE = os.path.join(STATE_DIR, "days.csv")
RUNS_FILE = os.path.join(STATE_DIR, "runs.log")
KILL_FILE = os.path.join(ROOT, "state", "KILL")


# ---------------------------------------------------------------- time helpers
def slot_start(date, slot):
    d = datetime.fromisoformat(date).replace(hour=9, minute=30, tzinfo=NY) + timedelta(minutes=5 * slot)
    return d.astimezone(timezone.utc)


def slot_of(ts):
    """Alpaca bar time (UTC ISO) -> (date in New York, slot) ; slot outside 0..77 means outside the session."""
    t = datetime.fromisoformat(ts.replace("Z", "+00:00")).astimezone(NY)
    return t.date().isoformat(), (t.hour * 60 + t.minute - 570) // 5


def iso(dt):
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# ---------------------------------------------------------------- data
class History:
    """Same shape the research features expect: bars (S, D, 78, 5), valid (S, D), dates (D,)."""

    def __init__(self, symbols, dates, raw):
        self.symbols, self.dates = symbols, np.array(dates)
        self.bars = np.zeros((len(symbols), len(dates), SLOTS, 5), dtype=np.float32)
        self.valid = np.zeros((len(symbols), len(dates)), dtype=bool)
        col = {d: k for k, d in enumerate(dates)}
        for i, s in enumerate(symbols):
            by_day = {}
            for b in raw.get(s, []):
                d, slot = slot_of(b["t"])
                if d in col and 0 <= slot < SLOTS:
                    by_day.setdefault(d, {})[slot] = (b["o"], b["h"], b["l"], b["c"], b["v"])
            for d, by in by_day.items():
                self.bars[i, col[d]], self.valid[i, col[d]] = day_to_array(by, d)


def morning_features(client, symbols, today):
    """{symbol: [prev_close, sigma60]} for today, from the prior sessions (today's column is left empty)."""
    start = (datetime.fromisoformat(today) - timedelta(days=60)).date().isoformat()
    cal = [c["date"] for c in client.calendar(start, today)]
    prior = [d for d in cal if d < today][-C.HISTORY_DAYS:]
    raw = client.bars(symbols, iso(slot_start(prior[0], 0)), iso(slot_start(prior[-1], SLOTS)), feed="sip")
    h = History(symbols, prior + [today], raw)
    # Today has no bars yet. sigma60 only fills days marked valid, and today's value uses only the PRIOR days
    # (cumulative sums up to, not including, today), so marking today valid changes nothing but the lookup.
    h.valid[:, -1] = True
    pc, sg = F.prev_close(h)[:, -1], F.sigma60(h)[:, -1]
    return {s: [None if not np.isfinite(pc[i]) else float(pc[i]), None if not np.isfinite(sg[i]) else float(sg[i])]
            for i, s in enumerate(symbols)}


def today_ctx(client, symbols, today, feats, upto_slot, feed="iex"):
    """Today's bars up to and including `upto_slot` in the backtest's ctx format."""
    raw = client.bars(symbols, iso(slot_start(today, 0)), iso(slot_start(today, upto_slot + 1)), feed=feed)
    S = len(symbols)
    bars = np.zeros((S, SLOTS, 5), dtype=np.float32)
    valid = np.zeros(S, dtype=bool)
    for i, s in enumerate(symbols):
        by = {}
        for b in raw.get(s, []):
            d, slot = slot_of(b["t"])
            if d == today and 0 <= slot <= upto_slot:
                by[slot] = (b["o"], b["h"], b["l"], b["c"], b["v"])
        prev = by[0][0] if 0 in by else None
        for k in range(upto_slot + 1):
            if k in by:
                bars[i, k] = by[k]
                prev = by[k][3]
            elif prev is not None:
                bars[i, k] = (prev, prev, prev, prev, 0)
        bad = any(max((b[1] - max(b[0], b[3])) / b[3], (min(b[0], b[3]) - b[2]) / b[3]) > MAX_WICK for b in by.values())
        valid[i] = 0 in by and not bad and feats.get(s, [None, None])[1] is not None
    pc = np.array([feats.get(s, [None])[0] or np.nan for s in symbols], dtype=np.float64)
    sg = np.array([feats.get(s, [None, None])[1] or np.nan for s in symbols], dtype=np.float64)
    return {"bars": bars, "valid": valid, "date": today, "sigma60": sg, "prev_close": pc}


# ---------------------------------------------------------------- state and logs
def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f:
            return json.load(f)
    return {"date": None, "features": {}, "done_slots": [], "positions": [], "closed": [], "halted": False,
            "summary_written": True}


def save_state(st):
    os.makedirs(STATE_DIR, exist_ok=True)
    with open(STATE_FILE, "w") as f:
        json.dump(st, f, indent=1)


def append_csv(path, row):
    os.makedirs(STATE_DIR, exist_ok=True)
    new = not os.path.exists(path)
    with open(path, "a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(row))
        if new:
            w.writeheader()
        w.writerow(row)


def log_run(line):
    os.makedirs(STATE_DIR, exist_ok=True)
    lines = open(RUNS_FILE).read().splitlines()[-1499:] if os.path.exists(RUNS_FILE) else []
    with open(RUNS_FILE, "w") as f:
        f.write("\n".join(lines + [line]) + "\n")


def trading_live():
    return os.environ.get("STOCKS_ENABLED", "").lower() == "true" and not os.path.exists(KILL_FILE)


# ---------------------------------------------------------------- the pass
def close_position(st, p, px, reason, now, notes):
    st.setdefault("_closed_this_pass", []).append(p)
    ret = px / p["entry"] - 1
    st["closed"].append({"sym": p["sym"], "ret": ret, "pnl": (px - p["entry"]) * p["qty"]})
    append_csv(TRADES_FILE, {"date": st["date"], "symbol": p["sym"], "decision": p["decision_time"],
                             "entry_time": p["entry_time"], "entry": round(p["entry"], 4), "exit_time": iso(now),
                             "exit": round(px, 4), "reason": reason, "qty": p["qty"], "ret_pct": round(ret * 100, 3),
                             "pnl_usd": round((px - p["entry"]) * p["qty"], 2), "z": p.get("z"),
                             "strategy": C.STRATEGY.name})
    notes.append(f"EXIT {p['sym']} {reason} @ {px:.2f} ({ret * 100:+.2f}%)")
    st["positions"].remove(p)


def sell_now(client, st, p, reason, now, live, last_px, notes):
    if live:
        if p.get("stop_order_id"):
            client.cancel(p["stop_order_id"])
        o = client.wait_filled(client.sell(p["sym"], p["qty"], f"{C.ORDER_PREFIX}{reason}-{p['sym']}-{p['entry_slot']}-{st['date']}")["id"])
        px = float(o.get("filled_avg_price") or last_px or p["entry"])
    else:
        px = last_px or p["entry"]
    close_position(st, p, px, reason, now, notes)


def step(client, now, st, live, strategy=None, symbols=None):
    strategy, symbols = strategy or C.STRATEGY, symbols or C.SYMBOLS
    notes = []
    today = now.astimezone(NY).date().isoformat()
    clock = client.clock()
    if not clock.get("is_open"):
        if st["positions"]:
            notes.append(f"WARNING market closed with {len(st['positions'])} open position(s) in state")
        return notes or ["market closed"]

    if st["date"] != today:
        if st["positions"]:
            notes.append(f"WARNING {len(st['positions'])} position(s) left from {st['date']}; dropping from state")
        st.update({"date": today, "features": morning_features(client, symbols, today), "done_slots": [],
                   "positions": [], "closed": [], "halted": False, "summary_written": False})
        n_ok = sum(1 for v in st["features"].values() if v[1] is not None)
        notes.append(f"new day: features for {n_ok}/{len(symbols)} stocks")
    if today in EARLY:
        return notes + ["early-close day: not trading (the backtest skips these days)"]

    completed = next((k for k in range(SLOTS - 1, -1, -1) if slot_start(today, k + 1) <= now), -1)
    flat_time = slot_start(today, C.FLAT_SLOT)

    # 1) manage open positions: stop fills, time exits, the 15:55 flatten
    st["_closed_this_pass"] = []
    for p in list(st["positions"]):
        if live and p.get("stop_order_id"):
            o = client.order(p["stop_order_id"])
            if o.get("status") == "filled":
                p["exit_slot"] = -1          # stop fills happen during a past bar: slot is free, as in the engine
                close_position(st, p, float(o["filled_avg_price"]), "stop", now, notes)
                continue
        exit_at = datetime.fromisoformat(p["exit_at"].replace("Z", "+00:00"))
        if now >= exit_at or now >= flat_time:
            sell_now(client, st, p, "time" if now < flat_time else "flat", now, live, None, notes)

    # 2) daily loss stop
    pnl = sum(c["pnl"] for c in st["closed"])
    equity = client.equity()
    if not st["halted"] and pnl <= -C.DAILY_LOSS_STOP * equity:
        st["halted"] = True
        notes.append(f"DAILY LOSS STOP: {pnl:,.0f} USD; selling everything, no more entries today")
        for p in list(st["positions"]):
            sell_now(client, st, p, "loss-stop", now, live, None, notes)

    # 3) decisions
    for slot in strategy.decision_slots:
        if slot > completed or slot in st["done_slots"]:
            continue
        st["done_slots"].append(slot)
        late = (now - slot_start(today, slot + 1)).total_seconds() / 60
        if late > C.LATE_ENTRY_MINUTES:
            notes.append(f"MISSED decision {slot_start(today, slot + 1).astimezone(NY):%H:%M} (pass {late:.0f} min late)")
            continue
        if st["halted"] or now >= flat_time:
            continue
        # Same capacity rule as the backtest: a position sold at this bar's open (exit slot slot+1) still counts
        # as occupying its slot for this decision (the engine frees a slot only when exit_slot <= decision slot).
        still_counted = [p for p in st["_closed_this_pass"] if p.get("exit_slot", -1) > slot]
        room = strategy.K - len(st["positions"]) - len(still_counted)
        if room <= 0:
            notes.append("decision skipped: all slots full")
            continue
        ctx = today_ctx(client, symbols, today, st["features"], slot)
        held = {symbols.index(p["sym"]) for p in st["positions"] + still_counted}
        picks = strategy.select(ctx, slot, held)[:room]
        z = strategy.scores(ctx, slot) if hasattr(strategy, "scores") else None
        when = slot_start(today, slot + 1).astimezone(NY).strftime("%H:%M")
        if not picks:
            best = int(np.nanargmin(np.where(ctx["valid"], z, np.nan))) if z is not None and ctx["valid"].any() else None
            notes.append(f"{when} decision: no stock past the trigger" +
                         (f" (closest: {symbols[best]} z={z[best]:.2f}, needs <= -{strategy.Z:g})"
                          if best is not None and hasattr(strategy, "Z") else ""))
            continue
        per_slot = equity * C.BUDGET_PCT / strategy.K
        for i, stop_frac, hold in picks:
            sym, ref = symbols[i], float(ctx["bars"][i, slot, 3])
            qty = math.floor(per_slot / ref)
            if qty < 1:
                notes.append(f"skip {sym}: price {ref:.2f} above per-trade budget")
                continue
            es = slot + 1
            exit_slot = min(es + hold, C.FLAT_SLOT)
            coid = f"{C.ORDER_PREFIX}entry-{sym}-{es}-{today}"
            if live:
                o = client.wait_filled(client.buy(sym, qty, coid)["id"])
                if o.get("status") != "filled":
                    notes.append(f"entry {sym} not filled ({o.get('status')})")
                    continue
                entry, qty = float(o["filled_avg_price"]), int(float(o["filled_qty"]))
            else:
                entry = ref
            p = {"sym": sym, "qty": qty, "entry": entry, "entry_slot": es, "exit_slot": exit_slot, "entry_time": iso(now),
                 "decision_time": when, "exit_at": iso(slot_start(today, exit_slot)),
                 "stop": entry * (1 - stop_frac) if stop_frac else None, "stop_order_id": None,
                 "z": round(float(z[i]), 2) if z is not None else None}
            if live and p["stop"]:
                p["stop_order_id"] = client.stop(sym, qty, p["stop"], f"{C.ORDER_PREFIX}stop-{sym}-{es}-{today}")["id"]
            st["positions"].append(p)
            notes.append(f"ENTRY {sym} x{qty} @ {entry:.2f} (z {p['z']}), stop {p['stop']:.2f}, "
                         f"exit by {slot_start(today, exit_slot).astimezone(NY):%H:%M}")

    # 4) end-of-day summary
    if now >= flat_time and not st["positions"] and not st["summary_written"]:
        rets = [c["ret"] for c in st["closed"]]
        append_csv(DAYS_FILE, {"date": today, "trades": len(rets), "wins": sum(r > 0 for r in rets),
                               "avg_ret_pct": round(float(np.mean(rets)) * 100, 3) if rets else 0.0,
                               "pnl_usd": round(sum(c["pnl"] for c in st["closed"]), 2),
                               "strategy": C.STRATEGY.name})
        st["summary_written"] = True
        notes.append(f"day summary: {len(rets)} trades, P&L {sum(c['pnl'] for c in st['closed']):,.2f} USD")
    if not notes:
        notes.append(f"{len(st['positions'])} open, watching")
    return notes


def safe_error(e):
    msg = str(e)
    if "header" in msg.lower():
        return f"{type(e).__name__}: bad request header (check the Alpaca secrets)"
    for name in ("ALPACA_API_KEY", "ALPACA_SECRET_KEY"):
        v = os.environ.get(name, "").strip()
        if len(v) >= 6:
            msg = msg.replace(v, "[redacted]")
    return f"{type(e).__name__}: {msg[:300]}"


def main():
    from stockbot.client import StockClient
    now = datetime.now(timezone.utc)
    et = now.astimezone(NY)
    if et.weekday() >= 5 or not (9 * 60 + 29 <= et.hour * 60 + et.minute <= 16 * 60 + 5):
        return                                   # outside market hours: exit quietly, nothing logged
    live = trading_live()
    st = load_state()
    mode = "PAPER" if live else "DRY"
    try:
        notes = step(StockClient.from_env(), now, st, live)
        st.pop("_closed_this_pass", None)
        save_state(st)
        log_run(f"{iso(now)} {mode} {C.STRATEGY.name}: " + "; ".join(notes))
    except Exception as e:
        save_state(st)
        log_run(f"{iso(now)} {mode} ERROR {safe_error(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
