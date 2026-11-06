# Risk limits (owned by the risk agent; changes need Idan's APPROVE)

## Shared paper account
- BTC bot (runner/, live): up to 25% of equity in BTC/USD, one position, stop on Alpaca. Order ids start with
  "entry-", "stop-", "target-", "time-", "signal-".
- Stock bot (not built yet): its own budget (proposal: 50% of equity across up to 5 positions), order ids prefixed
  "stk-", never reads or closes BTC/USD, flat by 15:55, daily loss stop.

## Research limits
- Max 4 variants per card. Holdout once per card, only with Idan's APPROVE.
