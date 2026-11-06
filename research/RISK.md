# Risk limits (owned by the risk agent; changes need Idan's APPROVE)

## Shared paper account
- BTC bot (runner/, live): up to 25% of equity in BTC/USD, one position, stop on Alpaca. Order ids start with
  "entry-", "stop-", "target-", "time-", "signal-".
- Stock bot (stockbot/, built 2026-11-06): 50% of equity across up to 5 positions (10% each, whole shares),
  stop order on Alpaca per position, flat from 15:55, skips early-close days, daily loss stop -2% of equity,
  order ids prefixed "stk-", never reads or closes BTC/USD. Runs H001 as a learning bot until a card passes.

## Research limits
- Max 4 variants per card. Holdout once per card, only with Idan's APPROVE.
