# Stock bot check: 2026-11-05 replayed with real data (no orders)

Strategy: H001 reversal_z3_h24 (learning bot: failed the research gate). Run at 2026-11-06 21:10 UTC.

- Features (prev close + sigma60 from the prior 25 sessions, SIP): 100/100 stocks.

- 5-minute bars with trades: IEX 7,766 vs SIP 7,800 (100%). Median close difference IEX vs SIP: 1.7 bp.
- Stocks valid today: IEX 100, SIP 100.

| Decision | Picks with IEX (live) | Picks with SIP (backtest data) | Lowest z (IEX) |
|---|---|---|---|
| 10:30 | MS, GS, BIDU, FCX, JPM | MS, GS, FCX, BIDU, JPM | MS -11.22, GS -10.57, BIDU -9.91 |
| 11:30 | ABBV, WFC, PFE, MO, WMT | PFE, ABBV, WFC, MO, KR | ABBV -3.99, WFC -3.91, PFE -3.86 |
| 12:30 | AVGO, LYB, DD, RTX | AVGO, DD, LYB, RTX | AVGO -3.13, LYB -3.07, DD -3.04 |
| 13:30 | none | none | RTX -1.93, GOOGL -1.53, TXN -1.51 |
| 14:30 | none | none | BRK.B -2.92, V -1.49, PYPL -1.47 |

A pick needs z <= -3. Different picks between IEX and SIP show the cost of the free data feed.
