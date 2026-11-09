"""Download daily bars for the multi-day research: the 100 stocks, ~20 ETFs, and BTC/USD.

Run on your PC (it needs internet):   py -m daily.download
Keys: ALPACA_API_KEY / ALPACA_SECRET_KEY from the environment, else from ./.env, else from ../Day-Trading-Lab/.env.
Keys are only sent to Alpaca's data API and are never printed. Read-only: no orders, no account calls.
Output: daily/cache/<SYMBOL>.json  ({"bars": [[date, o, h, l, c, v], ...]}), git-ignored. Dividend- and split-adjusted.
"""
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
CACHE = os.path.join(HERE, "cache")
DATA = "https://data.alpaca.markets"
START = "2015-06-01"   # extra year before 2016 so 200-day and 12-month signals exist from the start

ETFS = ["SPY", "QQQ", "IWM", "DIA", "EFA", "EEM", "VNQ", "TLT", "IEF", "SHY", "LQD", "GLD", "SLV", "DBC",
        "XLB", "XLE", "XLF", "XLI", "XLK", "XLP", "XLU", "XLV", "XLY"]


def load_keys():
    k, s = os.environ.get("ALPACA_API_KEY", ""), os.environ.get("ALPACA_SECRET_KEY", "")
    for path in (os.path.join(ROOT, ".env"), os.path.join(os.path.dirname(ROOT), "Day-Trading-Lab", ".env")):
        if k and s:
            break
        if os.path.exists(path):
            for line in open(path, encoding="utf-8"):
                if "=" in line and not line.lstrip().startswith("#"):
                    name, val = line.split("=", 1)
                    val = val.strip().strip('"').strip("'")
                    if name.strip() == "ALPACA_API_KEY" and not k:
                        k = val
                    if name.strip() == "ALPACA_SECRET_KEY" and not s:
                        s = val
    if not (k and s):
        sys.exit("No Alpaca keys found (env, .env, or ../Day-Trading-Lab/.env). Nothing downloaded.")
    return k.strip(), s.strip()


def get(path, params, keys, tries=5):
    url = DATA + path + "?" + urllib.parse.urlencode(params)
    headers = {"APCA-API-KEY-ID": keys[0], "APCA-API-SECRET-KEY": keys[1]} if keys else {}
    for n in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=30) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503, 504) and n < tries - 1:
                time.sleep(2 ** n)
                continue
            raise RuntimeError(f"HTTP {e.code} for {path}") from None
        except urllib.error.URLError:
            if n < tries - 1:
                time.sleep(2 ** n)
                continue
            raise RuntimeError(f"network error for {path}") from None


def stock_bars(sym, keys, end):
    out, token = [], None
    while True:
        p = {"symbols": sym, "timeframe": "1Day", "start": START, "end": end, "adjustment": "all",
             "feed": "sip", "limit": 10000}
        if token:
            p["page_token"] = token
        js = get("/v2/stocks/bars", p, keys)
        out += [[b["t"][:10], b["o"], b["h"], b["l"], b["c"], b["v"]] for b in js.get("bars", {}).get(sym, [])]
        token = js.get("next_page_token")
        if not token:
            return out


def crypto_bars(sym, keys, end):
    out, token = [], None
    while True:
        p = {"symbols": sym, "timeframe": "1Day", "start": START, "end": end, "limit": 10000}
        if token:
            p["page_token"] = token
        js = get("/v1beta3/crypto/us/bars", p, keys)
        out += [[b["t"][:10], b["o"], b["h"], b["l"], b["c"], b["v"]] for b in js.get("bars", {}).get(sym, [])]
        token = js.get("next_page_token")
        if not token:
            return out


def main():
    sys.path.insert(0, ROOT)
    from stockbot.config import SYMBOLS
    keys = load_keys()
    os.makedirs(CACHE, exist_ok=True)
    end = time.strftime("%Y-%m-%d", time.gmtime(time.time() - 86400))   # through yesterday (sip needs >15 min old)
    todo = [(s, "stock") for s in ETFS + sorted(SYMBOLS)] + [("BTC/USD", "crypto")]
    failed = []
    for k, (sym, kind) in enumerate(todo, 1):
        try:
            bars = stock_bars(sym, keys, end) if kind == "stock" else crypto_bars(sym, keys, end)
        except RuntimeError as e:
            failed.append(f"{sym} ({e})")
            print(f"[{k}/{len(todo)}] {sym}: FAILED {e}", flush=True)
            continue
        with open(os.path.join(CACHE, sym.replace("/", "") + ".json"), "w") as f:
            json.dump({"symbol": sym, "kind": kind, "etf": sym in ETFS, "bars": bars}, f)
        print(f"[{k}/{len(todo)}] {sym}: {len(bars)} days {bars[0][0] if bars else '-'} to {bars[-1][0] if bars else '-'}",
              flush=True)
    print(f"done: {len(todo) - len(failed)} ok, {len(failed)} failed" + (": " + ", ".join(failed) if failed else ""))


if __name__ == "__main__":
    main()
