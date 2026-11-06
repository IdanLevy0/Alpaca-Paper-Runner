"""Alpaca stock client for the paper bot. Plain HTTPS. PAPER ONLY (reuses the BTC bot's paper guard)."""
import os
import time

import requests

from runner.alpaca import PAPER_TRADING_URL, DATA_URL, assert_paper

TIMEOUT = 20


class StockClient:
    def __init__(self, key, secret, trading_url=PAPER_TRADING_URL):
        assert_paper(trading_url)
        self.url = trading_url.rstrip("/")
        self.s = requests.Session()
        self.s.headers.update({"APCA-API-KEY-ID": key.strip(), "APCA-API-SECRET-KEY": secret.strip()})

    @classmethod
    def from_env(cls):
        key, secret = os.environ.get("ALPACA_API_KEY", "").strip(), os.environ.get("ALPACA_SECRET_KEY", "").strip()
        if not key or not secret:
            raise RuntimeError("ALPACA_API_KEY / ALPACA_SECRET_KEY are missing")
        return cls(key, secret)

    def _req(self, method, url, allow_404=False, **kw):
        for attempt in range(5):
            r = self.s.request(method, url, timeout=TIMEOUT, **kw)
            if r.status_code != 429 and r.status_code < 500:
                break
            time.sleep(2 ** attempt)
        if allow_404 and r.status_code == 404:
            return None
        r.raise_for_status()
        return r.json() if r.content else None

    # account / clock
    def clock(self):
        return self._req("GET", self.url + "/v2/clock")

    def calendar(self, start, end):
        return self._req("GET", self.url + "/v2/calendar", params={"start": start, "end": end})

    def equity(self):
        return float(self._req("GET", self.url + "/v2/account")["equity"])

    # data
    def bars(self, symbols, start, end, feed):
        """5-minute bars for many symbols: {symbol: [bar, ...]} oldest first, split-adjusted."""
        out, token = {}, None
        while True:
            p = {"symbols": ",".join(symbols), "timeframe": "5Min", "start": start, "end": end, "feed": feed,
                 "adjustment": "split", "limit": 10000, "sort": "asc"}
            if token:
                p["page_token"] = token
            d = self._req("GET", DATA_URL + "/v2/stocks/bars", params=p)
            for sym, bs in (d.get("bars") or {}).items():
                out.setdefault(sym, []).extend(bs)
            token = d.get("next_page_token")
            if not token:
                return out

    # trading
    def position_qty(self, symbol):
        pos = self._req("GET", self.url + "/v2/positions/" + symbol.replace(".", "%2E"), allow_404=True)
        return float(pos["qty"]) if pos else 0.0

    def order(self, order_id):
        return self._req("GET", self.url + "/v2/orders/" + order_id)

    def cancel(self, order_id):
        self._req("DELETE", self.url + "/v2/orders/" + order_id, allow_404=True)

    def buy(self, symbol, qty, coid):
        return self._req("POST", self.url + "/v2/orders", json={
            "symbol": symbol, "qty": str(int(qty)), "side": "buy", "type": "market", "time_in_force": "day",
            "client_order_id": coid})

    def sell(self, symbol, qty, coid):
        return self._req("POST", self.url + "/v2/orders", json={
            "symbol": symbol, "qty": str(int(qty)), "side": "sell", "type": "market", "time_in_force": "day",
            "client_order_id": coid})

    def stop(self, symbol, qty, stop_price, coid):
        return self._req("POST", self.url + "/v2/orders", json={
            "symbol": symbol, "qty": str(int(qty)), "side": "sell", "type": "stop", "time_in_force": "day",
            "stop_price": f"{stop_price:.2f}", "client_order_id": coid})

    def wait_filled(self, order_id, tries=15):
        for _ in range(tries):
            o = self.order(order_id)
            if o["status"] in ("filled", "canceled", "rejected", "expired"):
                return o
            time.sleep(1)
        return self.order(order_id)
