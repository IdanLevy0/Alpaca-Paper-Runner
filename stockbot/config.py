"""Stock paper bot settings. The strategy comes from stocks/strategies.py so live and backtest share the rules."""
from stocks.strategies import Reversal

# H001 best training variant, run as a LEARNING BOT (it failed the research gate after costs).
# Swap for a card that passes the Skeptic + holdout + Idan's approval.
STRATEGY = Reversal(Z=3.0, H=24, K=5)
LABEL = "H001 reversal_z3_h24 (learning bot: failed the research gate)"

SYMBOLS = ['AAL', 'AAPL', 'ABBV', 'ACN', 'ADBE', 'AIG', 'AMGN', 'AMZN', 'AVGO', 'AXP', 'BA', 'BABA', 'BAC', 'BHC',
           'BIDU', 'BIIB', 'BKNG', 'BMY', 'BRK.B', 'C', 'CAT', 'CHTR', 'CMCSA', 'CMG', 'COP', 'COST', 'CRM', 'CSCO',
           'CVS', 'CVX', 'DAL', 'DD', 'DIS', 'DVN', 'EBAY', 'EOG', 'EQIX', 'F', 'FCX', 'GE', 'GILD', 'GM', 'GOOG',
           'GOOGL', 'GS', 'HAL', 'HD', 'HON', 'IBM', 'INTC', 'JNJ', 'JPM', 'KMI', 'KO', 'KR', 'LLY', 'LMT', 'LOW',
           'LYB', 'MA', 'MCD', 'MCK', 'MDLZ', 'MDT', 'MET', 'META', 'MMM', 'MO', 'MRK', 'MS', 'MSFT', 'NFLX', 'NKE',
           'ORCL', 'OXY', 'PEP', 'PFE', 'PG', 'PM', 'PSX', 'PYPL', 'QCOM', 'REGN', 'RTX', 'SBUX', 'SLB', 'T', 'TGT',
           'TSLA', 'TXN', 'UNH', 'UNP', 'UPS', 'USB', 'V', 'VLO', 'VZ', 'WFC', 'WMT', 'XOM']

BUDGET_PCT = 0.05          # share of paper equity the stock bot may use; each of K slots gets BUDGET_PCT / K
DAILY_LOSS_STOP = 0.02     # stop opening trades (and flatten) if today's stock P&L falls below -2% of equity
LATE_ENTRY_MINUTES = 10    # act on a decision only if the pass runs within this many minutes of the bar close
FLAT_SLOT = 77             # everything is sold from 15:55 on
HISTORY_DAYS = 25          # prior sessions fetched each morning for sigma60 (needs 20 valid ones)
ORDER_PREFIX = "stk-"
