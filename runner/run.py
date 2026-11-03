"""One pass of the paper runner. Runs every 5 minutes (GitHub Actions cron).

Entries are judged once per new completed 4h candle (the strategies are defined on candle closes).
Exits: the stop sits on Alpaca and fires on its own; the target and time exit are checked every pass.

Orders are only sent when TRADING_ENABLED=true and the file state/KILL does not exist.
Otherwise it runs in dry mode: same decisions, logged, no orders.
"""
import csv
import json
import os
import sys
from datetime import datetime, timedelta, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from runner import config                                  # noqa: E402
from runner.strategies import STRATEGIES, LOOKBACK         # noqa: E402

STATE_DIR = os.path.join(ROOT, "state")
STATE_FILE = os.path.join(STATE_DIR, "state.json")
TRADES_FILE = os.path.join(STATE_DIR, "trades.csv")
RUNS_FILE = os.path.join(STATE_DIR, "runs.log")
KILL_FILE = os.path.join(STATE_DIR, "KILL")


def ts(s):
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def iso(dt):
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f:
            return json.load(f)
    return {"in_trade": False, "last_signal_bar": None, "entries": {}}


def save_state(st):
    os.makedirs(STATE_DIR, exist_ok=True)
    with open(STATE_FILE, "w") as f:
        json.dump(st, f, indent=2)


def log_trade(row):
    new = not os.path.exists(TRADES_FILE)
    with open(TRADES_FILE, "a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["strategy", "entry_time", "entry", "exit_time", "exit", "reason", "qty", "ret_pct"])
        if new:
            w.writeheader()
        w.writerow(row)


def log_run(line):
    os.makedirs(STATE_DIR, exist_ok=True)
    lines = open(RUNS_FILE).read().splitlines()[-499:] if os.path.exists(RUNS_FILE) else []
    lines.append(line)
    with open(RUNS_FILE, "w") as f:
        f.write("\n".join(lines) + "\n")


def completed(bars, now, secs):
    return [b for b in bars if ts(b["t"]) + timedelta(seconds=secs) <= now]


def close_trade(st, exit_px, reason, now, notes):
    ret = (exit_px / st["entry"] - 1) * 100
    log_trade({"strategy": st["strategy"], "entry_time": st["entry_time"], "entry": round(st["entry"], 2),
               "exit_time": iso(now), "exit": round(exit_px, 2), "reason": reason, "qty": st["qty"],
               "ret_pct": round(ret, 3)})
    notes.append(f"EXIT {reason} @ {exit_px:.2f} ({ret:+.2f}% before fees)")
    for k in ("entry_time", "entry", "stop", "target", "max_bars", "qty", "stop_order_id", "entry_bar_t", "strategy"):
        st.pop(k, None)
    st["in_trade"] = False


def step(client, now, st, live):
    """One decision pass. Returns a list of notes for the run log."""
    sym, notes = config.SYMBOL, []
    start4 = iso(now - timedelta(seconds=config.BAR_SECONDS * (LOOKBACK + 10)))
    bars = completed(client.bars(sym, config.TIMEFRAME, start4), now, config.BAR_SECONDS)[-LOOKBACK:]
    if not bars:
        return ["no bars"]
    pos = client.position_qty(sym)

    if st["in_trade"]:
        if pos <= 0:
            # Stop filled on the exchange (or position closed by hand)
            px = st["stop"]
            if st.get("stop_order_id"):
                o = client.order(st["stop_order_id"])
                if o.get("filled_avg_price"):
                    px = float(o["filled_avg_price"])
            close_trade(st, px, "stop", now, notes)
        else:
            if not st.get("stop_order_id") and live:
                o = client.sell_stop(sym, pos, st["stop"], f"stop-{st['entry_bar_t']}")
                st["stop_order_id"] = o["id"]
                notes.append(f"placed stop {st['stop']:.2f}")
            since = st.get("last_check") or st["entry_time"]
            # 5-minute bars since the last check, including the one still forming: any touch of the target counts
            recent = [b for b in client.bars(sym, "5Min", since) if ts(b["t"]) <= now]
            hit_target = any(b["h"] >= st["target"] for b in recent)
            held = sum(1 for b in bars if b["t"] >= st["entry_bar_t"])
            reason = "target" if hit_target else ("time" if held >= st["max_bars"] else None)
            if reason:
                if live:
                    if st.get("stop_order_id"):
                        client.cancel(st["stop_order_id"])
                    o = client.wait_filled(client.sell_market(sym, pos, f"{reason}-{st['entry_bar_t']}")["id"])
                    px = float(o.get("filled_avg_price") or bars[-1]["c"])
                else:
                    px = st["target"] if reason == "target" else bars[-1]["c"]
                close_trade(st, px, reason, now, notes)
            else:
                notes.append(f"holding, {held}/{st['max_bars']} bars, stop {st['stop']:.2f} target {st['target']:.2f}")
        st["last_check"] = iso(now)
        return notes

    if pos > 0:
        return [f"WARNING: holding {pos} {sym} the runner did not open; doing nothing"]

    last = bars[-1]["t"]
    if st.get("last_signal_bar") == last:
        return [f"flat, bar {last} already checked"]
    st["last_signal_bar"] = last
    name = config.STRATEGY
    sig = STRATEGIES[name](bars)
    if not sig:
        return [f"flat, no signal on {last}"]

    day = iso(now)[:10]
    if st["entries"].get(day, 0) >= config.MAX_ENTRIES_PER_DAY:
        return ["signal skipped: daily entry cap reached"]
    notional = min(client.equity() * config.POSITION_PCT, config.MAX_NOTIONAL)
    if live:
        o = client.wait_filled(client.buy_notional(sym, notional, f"entry-{last}")["id"])
        entry, qty = float(o["filled_avg_price"]), float(o["filled_qty"])
    else:
        entry, qty = bars[-1]["c"], round(notional / bars[-1]["c"], 6)
    entry_bar = ts(last) + timedelta(seconds=config.BAR_SECONDS)
    st.update({"in_trade": True, "strategy": name, "entry_time": iso(now), "entry": entry, "qty": qty,
               "stop": entry - sig["stop_dist"], "target": entry + sig["target_dist"],
               "max_bars": sig["max_bars"], "entry_bar_t": iso(entry_bar), "stop_order_id": None,
               "last_check": iso(now)})
    st["entries"] = {day: st["entries"].get(day, 0) + 1}
    notes.append(f"ENTRY {name} @ {entry:.2f}, qty {qty}, stop {st['stop']:.2f}, target {st['target']:.2f}")
    if live:
        o = client.sell_stop(sym, qty, st["stop"], f"stop-{st['entry_bar_t']}")
        st["stop_order_id"] = o["id"]
    return notes


def trading_live():
    """Orders only when TRADING_ENABLED=true AND no state/KILL file."""
    return os.environ.get("TRADING_ENABLED", "").lower() == "true" and not os.path.exists(KILL_FILE)


def main():
    from runner.alpaca import AlpacaClient
    live = trading_live()
    now = datetime.now(timezone.utc)
    st = load_state()
    mode = "PAPER" if live else "DRY"
    try:
        notes = step(AlpacaClient.from_env(), now, st, live)
        save_state(st)
        log_run(f"{iso(now)} {mode} {config.STRATEGY}: " + "; ".join(notes))
    except Exception as e:  # log, then fail the job so GitHub shows a red run
        log_run(f"{iso(now)} {mode} ERROR {type(e).__name__}: {e}")
        raise


if __name__ == "__main__":
    main()
