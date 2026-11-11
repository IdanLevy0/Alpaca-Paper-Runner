"""Multi-strategy daily runner (stocks/ETFs). One pass per workflow run; acts once per trading day after 09:35 ET.

For each sleeve: rebuild the strategy's target weights from daily bars through YESTERDAY's close (same code and same
History view as the backtest), compare with the sleeve's own shares, and trade the difference with fractional market
orders. Sells go before buys. Each sleeve only ever sells shares it owns, so sleeves never interfere with each other or
with the intraday stock bot / BTC bot. State: state/daily/state.json; fills: state/daily/trades.csv;
end-of-day sleeve values: state/daily/values.csv.
"""
import csv
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from daily import config as C                     # noqa: E402
from daily.data import Panel                      # noqa: E402
from daily.engine import decide                   # noqa: E402
from daily.strategies import CARDS                # noqa: E402

NY = ZoneInfo("America/New_York")
DIR = os.path.join(ROOT, "state", "daily")
STATE_FILE, TRADES_FILE = os.path.join(DIR, "state.json"), os.path.join(DIR, "trades.csv")
VALUES_FILE, RUNS_FILE = os.path.join(DIR, "values.csv"), os.path.join(DIR, "runs.log")
KILL_FILE = os.path.join(ROOT, "state", "KILL")
HISTORY_DAYS = 420            # calendar days of daily bars to fetch (covers 252 trading days + warm-up)


def strategy_for(card, name):
    for s in CARDS[card]():
        if s.name == name:
            return s
    raise KeyError(f"{card} has no variant {name}")


def slice_pct(sl):
    return C.BUDGET[sl["stage"]] * min(1.0, C.VOL_TARGET / max(sl["vol"], 1e-9))


def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f:
            return json.load(f)
    return {"last_rebalance": None, "sleeves": {}}


def save_state(st):
    os.makedirs(DIR, exist_ok=True)
    with open(STATE_FILE, "w") as f:
        json.dump(st, f, indent=1, sort_keys=True)


def append_csv(path, row):
    os.makedirs(DIR, exist_ok=True)
    new = not os.path.exists(path)
    with open(path, "a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(row))
        if new:
            w.writeheader()
        w.writerow(row)


def log_run(line):
    os.makedirs(DIR, exist_ok=True)
    lines = open(RUNS_FILE).read().splitlines()[-999:] if os.path.exists(RUNS_FILE) else []
    with open(RUNS_FILE, "w") as f:
        f.write("\n".join(lines + [line]) + "\n")


def build_panel(bars, today):
    """bars: {symbol: [(date, o, h, l, c, v), ...]} through yesterday. Adds today as the last calendar day (no prices)
    so strategies can see the calendar the same way as in the backtest."""
    syms = sorted(bars)
    dates = sorted({b[0] for v in bars.values() for b in v if b[0] < today}) + [today]
    pos = {d: k for k, d in enumerate(dates)}
    arr = {k: np.full((len(syms), len(dates)), np.nan) for k in "ohlcv"}
    for i, s in enumerate(syms):
        for b in bars[s]:
            if b[0] in pos and b[0] < today:
                for j, k in enumerate("ohlcv"):
                    arr[k][i, pos[b[0]]] = b[1 + j]
    from daily.download import ETFS
    etf = np.array([s in ETFS for s in syms])
    return Panel(syms, dates, arr["o"], arr["h"], arr["l"], arr["c"], arr["v"], etf)


def targets(panel, sl):
    """Weights the backtest would hold today: the latest decision made at or before yesterday's close."""
    st = strategy_for(sl["card"], sl["variant"])
    t = len(panel.dates) - 2                   # yesterday
    W, R = decide(panel, st, 0, t)
    return {panel.symbols[i]: float(w) for i, w in enumerate(W[t]) if w > 0}, bool(R[t])


def step(client, now, st, live, sleeves=None):
    sleeves = [s for s in C.SLEEVES if not s["card"].startswith("B")] if sleeves is None else sleeves
    notes = []
    et = now.astimezone(NY)
    today = et.date().isoformat()
    if not sleeves:
        return []                               # nothing approved to run yet
    clock = client.clock()
    if not clock.get("is_open"):
        return ["market closed"]
    if (et.hour, et.minute) < C.REBALANCE_AFTER_ET or st.get("last_rebalance") == today:
        return []
    syms = sorted({s for sl in sleeves for s in sl["universe"]})
    start = (et.date() - timedelta(days=HISTORY_DAYS)).isoformat()
    panel = build_panel(client.daily_bars(syms, start, today), today)
    equity = client.equity()
    prices = client.latest_prices(syms)
    plan = []
    for sl in sleeves:
        key = f"{sl['card']}:{sl['variant']}"
        mine = st["sleeves"].setdefault(key, {"shares": {}, "invested": 0.0})
        w, rebalance_day = targets(panel, sl)
        first = not mine["shares"] and mine["invested"] == 0.0
        if not (rebalance_day or first):
            continue
        budget = equity * slice_pct(sl)
        for s in sorted(set(w) | set(mine["shares"])):
            px = prices.get(s)
            if not px:
                notes.append(f"{key}: no price for {s}, skipped")
                continue
            have = mine["shares"].get(s, 0.0) * px
            diff = w.get(s, 0.0) * budget - have
            if abs(diff) >= C.MIN_ORDER_USD:
                plan.append((key, s, diff, px))
        notes.append(f"{key}: rebalance ({'first day' if first else 'rule day'}), {len(w)} holdings")
    for key, s, diff, px in sorted(plan, key=lambda p: p[2]):          # sells first
        mine = st["sleeves"][key]
        coid = f"{C.ORDER_PREFIX}{key.split(':')[0]}-{s}-{today}-{'s' if diff < 0 else 'b'}"
        if diff < 0:
            qty = min(mine["shares"].get(s, 0.0), round(-diff / px, 6))
            if qty <= 0:
                continue
            fill = client.wait_filled(client.sell_qty(s, qty, coid)["id"]) if live else \
                {"status": "filled", "filled_qty": qty, "filled_avg_price": px}
            sign = -1
        else:
            fill = client.wait_filled(client.buy_notional(s, round(diff, 2), coid)["id"]) if live else \
                {"status": "filled", "filled_qty": round(diff / px, 6), "filled_avg_price": px}
            sign = 1
        if fill.get("status") != "filled":
            notes.append(f"{key}: {s} order {fill.get('status')}")
            continue
        q, p = float(fill["filled_qty"]), float(fill["filled_avg_price"])
        mine["shares"][s] = round(mine["shares"].get(s, 0.0) + sign * q, 6)
        if mine["shares"][s] <= 1e-6:
            mine["shares"].pop(s)
        mine["invested"] = round(mine["invested"] + sign * q * p, 2)
        append_csv(TRADES_FILE, {"date": today, "time": now.isoformat(timespec="seconds"), "sleeve": key, "symbol": s,
                                 "side": "buy" if sign > 0 else "sell", "qty": q, "price": p,
                                 "decision_price": round(px, 4), "usd": round(q * p, 2)})
        notes.append(f"{key}: {'BUY' if sign > 0 else 'SELL'} {s} {q:g} @ {p:.2f}")
    st["last_rebalance"] = today
    for key, mine in st["sleeves"].items():
        value = sum(q * prices.get(s, 0.0) for s, q in mine["shares"].items())
        append_csv(VALUES_FILE, {"date": today, "sleeve": key, "value": round(value, 2), "invested": mine["invested"]})
    return notes


def step_crypto(client, now, st, live, sleeves):
    """BTC sleeves: once a day, on the first pass after 00:05 UTC, from daily bars through yesterday (UTC)."""
    notes = []
    today = now.astimezone(timezone.utc).date().isoformat()
    if not sleeves or (now.hour, now.minute) < (0, 5) or st.get("last_crypto_rebalance") == today:
        return notes
    sym = "BTC/USD"
    start = (now.date() - timedelta(days=HISTORY_DAYS)).isoformat()
    panel = build_panel(client.crypto_daily_bars(sym, start, today), today)
    equity, px = client.equity(), client.crypto_price(sym)
    for sl in sleeves:
        key = f"{sl['card']}:{sl['variant']}"
        mine = st["sleeves"].setdefault(key, {"shares": {}, "invested": 0.0})
        w, _ = targets(panel, sl)
        diff = w.get(sym, 0.0) * equity * slice_pct(sl) - mine["shares"].get(sym, 0.0) * px
        if abs(diff) < C.MIN_ORDER_USD:
            continue
        coid = f"{C.ORDER_PREFIX}{sl['card']}-BTC-{today}-{'s' if diff < 0 else 'b'}"
        if diff < 0:
            qty = min(mine["shares"].get(sym, 0.0), round(-diff / px, 9))
            fill = client.wait_filled(client.crypto_sell_qty(sym, qty, coid)["id"]) if live else \
                {"status": "filled", "filled_qty": qty, "filled_avg_price": px}
            sign = -1
        else:
            fill = client.wait_filled(client.crypto_buy_notional(sym, round(diff, 2), coid)["id"]) if live else \
                {"status": "filled", "filled_qty": round(diff / px, 9), "filled_avg_price": px}
            sign = 1
        if fill.get("status") != "filled":
            notes.append(f"{key}: BTC order {fill.get('status')}")
            continue
        q, p = float(fill["filled_qty"]), float(fill["filled_avg_price"])
        mine["shares"][sym] = round(mine["shares"].get(sym, 0.0) + sign * q, 9)
        if mine["shares"][sym] <= 1e-9:
            mine["shares"].pop(sym)
        mine["invested"] = round(mine["invested"] + sign * q * p, 2)
        append_csv(TRADES_FILE, {"date": today, "time": now.isoformat(timespec="seconds"), "sleeve": key, "symbol": sym,
                                 "side": "buy" if sign > 0 else "sell", "qty": q, "price": p,
                                 "decision_price": round(px, 2), "usd": round(q * p, 2)})
        notes.append(f"{key}: {'BUY' if sign > 0 else 'SELL'} BTC {q:g} @ {p:.2f}")
    st["last_crypto_rebalance"] = today
    return notes


def btc_held_by_sleeves(state_file=None):
    """BTC the daily sleeves own (the BTC bot subtracts this from the account position so the two never mix)."""
    try:
        with open(state_file or STATE_FILE) as f:
            st = json.load(f)
        return sum(v["shares"].get("BTC/USD", 0.0) for v in st.get("sleeves", {}).values())
    except (OSError, ValueError, KeyError):
        return 0.0


def trading_live():
    return os.environ.get("DAILY_ENABLED", "").strip().lower() == "true" and not os.path.exists(KILL_FILE)


def main():
    from daily.client import DailyClient
    from stockbot.live import safe_error
    now = datetime.now(timezone.utc)
    et = now.astimezone(NY)
    stock_sleeves = [s for s in C.SLEEVES if not s["card"].startswith("B")]
    crypto_sleeves = [s for s in C.SLEEVES if s["card"].startswith("B")]
    market_hours = et.weekday() < 5 and 9 * 60 + 30 <= et.hour * 60 + et.minute <= 15 * 60 + 30
    crypto_due = bool(crypto_sleeves) and (now.hour, now.minute) >= (0, 5)
    if not (market_hours or crypto_due):
        return
    live = trading_live()
    st = load_state()
    if crypto_due and st.get("last_crypto_rebalance") == now.date().isoformat() and not market_hours:
        return
    try:
        client = DailyClient.from_env()
        notes = step_crypto(client, now, st, live, crypto_sleeves) if crypto_due else []
        if market_hours:
            notes += step(client, now, st, live, stock_sleeves)
        save_state(st)
        if notes:
            log_run(f"{now.isoformat(timespec='seconds')} {'PAPER' if live else 'DRY'}: " + "; ".join(notes))
    except Exception as e:
        save_state(st)
        log_run(f"{now.isoformat(timespec='seconds')} ERROR {safe_error(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
