"""Weekend / pre-open check with REAL Alpaca data, no orders: replays the last full session through the live code.

python -m stockbot.check  ->  state/stocks/check.md
Shows: features loaded, IEX vs full-market (SIP) bar coverage, and the decisions the bot would have made at each
decision time with IEX (what it sees live) and with SIP (what the backtest used).
"""
import os
import sys
from datetime import datetime, timedelta, timezone

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from stockbot import config as C                                       # noqa: E402
from stockbot.live import morning_features, today_ctx, slot_start, NY, STATE_DIR, safe_error  # noqa: E402


def main():
    from stockbot.client import StockClient
    client = StockClient.from_env()
    now = datetime.now(timezone.utc)
    cal = client.calendar((now - timedelta(days=14)).date().isoformat(), now.date().isoformat())
    done = [c["date"] for c in cal if slot_start(c["date"], 78) + timedelta(minutes=20) <= now]
    day = done[-1]
    st = C.STRATEGY
    L = [f"# Stock bot check: {day} replayed with real data (no orders)", "",
         f"Strategy: {C.LABEL}. Run at {now:%Y-%m-%d %H:%M} UTC.", ""]
    feats = morning_features(client, C.SYMBOLS, day)
    ok = sum(1 for v in feats.values() if v[1] is not None)
    L += [f"- Features (prev close + sigma60 from the prior {C.HISTORY_DAYS} sessions, SIP): {ok}/{len(C.SYMBOLS)} stocks.", ""]
    full_iex = today_ctx(client, C.SYMBOLS, day, feats, 77, feed="iex")
    full_sip = today_ctx(client, C.SYMBOLS, day, feats, 77, feed="sip")
    iex_bars = int((full_iex["bars"][:, :, 4] > 0).sum())
    sip_bars = int((full_sip["bars"][:, :, 4] > 0).sum())
    diff = np.nanmedian(np.abs(full_iex["bars"][:, :, 3] / np.where(full_sip["bars"][:, :, 3] > 0, full_sip["bars"][:, :, 3], np.nan) - 1))
    L += [f"- 5-minute bars with trades: IEX {iex_bars:,} vs SIP {sip_bars:,} ({iex_bars / max(1, sip_bars) * 100:.0f}%). "
          f"Median close difference IEX vs SIP: {diff * 1e4:.1f} bp.",
          f"- Stocks valid today: IEX {int(full_iex['valid'].sum())}, SIP {int(full_sip['valid'].sum())}.", "",
          "| Decision | Picks with IEX (live) | Picks with SIP (backtest data) | Lowest z (IEX) |", "|---|---|---|---|"]
    for slot in st.decision_slots:
        when = slot_start(day, slot + 1).astimezone(NY).strftime("%H:%M")
        row = []
        for feed in ("iex", "sip"):
            ctx = today_ctx(client, C.SYMBOLS, day, feats, slot, feed=feed)
            picks = st.select(ctx, slot, set())[:st.K]
            row.append(", ".join(C.SYMBOLS[i] for i, *_ in picks) or "none")
            if feed == "iex":
                z = st.scores(ctx, slot)
                zz = np.where(ctx["valid"], z, np.nan)
                low = np.argsort(np.nan_to_num(zz, nan=99))[:3]
                lowest = ", ".join(f"{C.SYMBOLS[i]} {zz[i]:.2f}" for i in low if np.isfinite(zz[i]))
        L.append(f"| {when} | {row[0]} | {row[1]} | {lowest} |")
    L += ["", f"A pick needs z <= -{st.Z:g}. Different picks between IEX and SIP show the cost of the free data feed."]
    os.makedirs(STATE_DIR, exist_ok=True)
    with open(os.path.join(STATE_DIR, "check.md"), "w") as f:
        f.write("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        os.makedirs(STATE_DIR, exist_ok=True)
        with open(os.path.join(STATE_DIR, "check.md"), "w") as f:
            f.write(f"# Stock bot check FAILED\n\n{safe_error(e)}\n")
        print(safe_error(e))
        sys.exit(1)
