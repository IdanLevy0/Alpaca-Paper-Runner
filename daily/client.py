"""Alpaca client additions for the daily runner: daily bars, latest prices, fractional orders. PAPER ONLY."""
from runner.alpaca import DATA_URL
from stockbot.client import StockClient


class DailyClient(StockClient):
    def daily_bars(self, symbols, start, end):
        """{symbol: [(date, o, h, l, c, v), ...]} split- and dividend-adjusted, sip feed (bars before today only)."""
        out, token = {s: [] for s in symbols}, None
        while True:
            p = {"symbols": ",".join(symbols), "timeframe": "1Day", "start": start, "end": end, "feed": "sip",
                 "adjustment": "all", "limit": 10000, "sort": "asc"}
            if token:
                p["page_token"] = token
            d = self._req("GET", DATA_URL + "/v2/stocks/bars", params=p)
            for sym, bs in (d.get("bars") or {}).items():
                out[sym] += [(b["t"][:10], b["o"], b["h"], b["l"], b["c"], b["v"]) for b in bs]
            token = d.get("next_page_token")
            if not token:
                return out

    def latest_prices(self, symbols):
        d = self._req("GET", DATA_URL + "/v2/stocks/trades/latest", params={"symbols": ",".join(symbols), "feed": "iex"})
        return {s: float(t["p"]) for s, t in (d.get("trades") or {}).items()}

    def buy_notional(self, symbol, usd, coid):
        return self._req("POST", self.url + "/v2/orders", json={
            "symbol": symbol, "notional": f"{usd:.2f}", "side": "buy", "type": "market", "time_in_force": "day",
            "client_order_id": coid})

    def sell_qty(self, symbol, qty, coid):
        return self._req("POST", self.url + "/v2/orders", json={
            "symbol": symbol, "qty": f"{qty:.6f}", "side": "sell", "type": "market", "time_in_force": "day",
            "client_order_id": coid})
