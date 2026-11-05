"""Thin Alpaca client over plain HTTPS. PAPER ONLY: there is no live URL anywhere in this project."""
import os
import time
import requests

PAPER_TRADING_URL = "https://paper-api.alpaca.markets"
DATA_URL = "https://data.alpaca.markets"
TIMEOUT = 20


class NotPaperError(Exception):
    pass


def assert_paper(url):
    if url.rstrip("/") != PAPER_TRADING_URL:
        raise NotPaperError("trading URL is not the paper endpoint; refusing to start")


def _norm(b):
    return {"t": b["t"], "o": float(b["o"]), "h": float(b["h"]), "l": float(b["l"]),
            "c": float(b["c"]), "v": float(b.get("v", 0))}


def fetch_crypto_bars(symbol, timeframe, start, end=None, key=None, secret=None):
    """Bars oldest first. Crypto data works without keys; keys are sent if given."""
    s = requests.Session()
    key, secret = (key or "").strip(), (secret or "").strip()
    if key and secret:
        s.headers.update({"APCA-API-KEY-ID": key, "APCA-API-SECRET-KEY": secret})
    out, token = [], None
    while True:
        p = {"symbols": symbol, "timeframe": timeframe, "start": start, "limit": 10000, "sort": "asc"}
        if end:
            p["end"] = end
        if token:
            p["page_token"] = token
        for attempt in range(6):          # retry when throttled (429) or Alpaca hiccups (5xx)
            r = s.get(DATA_URL + "/v1beta3/crypto/us/bars", params=p, timeout=TIMEOUT)
            if r.status_code != 429 and r.status_code < 500:
                break
            time.sleep(2 ** attempt)
        r.raise_for_status()
        d = r.json()
        out.extend(_norm(b) for b in (d.get("bars") or {}).get(symbol, []))
        token = d.get("next_page_token")
        if not token:
            return out


class AlpacaClient:
    def __init__(self, key, secret, trading_url=PAPER_TRADING_URL):
        assert_paper(trading_url)
        self.key, self.secret = key, secret
        self.url = trading_url.rstrip("/")
        self.s = requests.Session()
        self.s.headers.update({"APCA-API-KEY-ID": key, "APCA-API-SECRET-KEY": secret})

    @classmethod
    def from_env(cls):
        key = os.environ.get("ALPACA_API_KEY", "").strip()
        secret = os.environ.get("ALPACA_SECRET_KEY", "").strip()
        if not key or not secret:
            raise RuntimeError("ALPACA_API_KEY / ALPACA_SECRET_KEY are missing")
        return cls(key, secret)

    def _req(self, method, path, allow_404=False, **kw):
        r = self.s.request(method, self.url + path, timeout=TIMEOUT, **kw)
        if allow_404 and r.status_code == 404:
            return None
        r.raise_for_status()
        return r.json() if r.content else None

    def bars(self, symbol, timeframe, start):
        return fetch_crypto_bars(symbol, timeframe, start, key=self.key, secret=self.secret)

    def equity(self):
        return float(self._req("GET", "/v2/account")["equity"])

    def position_qty(self, symbol):
        pos = self._req("GET", "/v2/positions/" + symbol.replace("/", ""), allow_404=True)
        return float(pos["qty"]) if pos else 0.0

    def order(self, order_id):
        return self._req("GET", "/v2/orders/" + order_id)

    def open_orders(self, symbol):
        return self._req("GET", "/v2/orders", params={"status": "open", "symbols": symbol}) or []

    def cancel(self, order_id):
        self._req("DELETE", "/v2/orders/" + order_id, allow_404=True)

    def submit(self, body):
        return self._req("POST", "/v2/orders", json=body)

    def buy_notional(self, symbol, notional, coid):
        return self.submit({"symbol": symbol, "notional": f"{notional:.2f}", "side": "buy", "type": "market",
                            "time_in_force": "gtc", "client_order_id": coid})

    def sell_market(self, symbol, qty, coid):
        return self.submit({"symbol": symbol, "qty": f"{qty:.9f}", "side": "sell", "type": "market",
                            "time_in_force": "gtc", "client_order_id": coid})

    def sell_stop(self, symbol, qty, stop, coid):
        """Protective stop that sits on the exchange: stop-limit with a 1% limit cushion."""
        return self.submit({"symbol": symbol, "qty": f"{qty:.9f}", "side": "sell", "type": "stop_limit",
                            "stop_price": f"{stop:.2f}", "limit_price": f"{stop * 0.99:.2f}",
                            "time_in_force": "gtc", "client_order_id": coid})

    def wait_filled(self, order_id, tries=10):
        for _ in range(tries):
            o = self.order(order_id)
            if o["status"] == "filled":
                return o
            time.sleep(1)
        return self.order(order_id)
