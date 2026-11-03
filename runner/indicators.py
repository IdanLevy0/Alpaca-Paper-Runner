"""Plain-Python indicators over lists of floats. Index i uses data up to and including bar i only."""


def ema(values, length):
    out, k, prev = [], 2.0 / (length + 1), None
    for i, v in enumerate(values):
        if i < length - 1:
            out.append(None)
            continue
        if prev is None:
            prev = sum(values[i - length + 1:i + 1]) / length
        else:
            prev = v * k + prev * (1 - k)
        out.append(prev)
    return out


def atr(bars, length=14):
    """Wilder ATR, same smoothing as TradingView's ta.atr."""
    trs = []
    for i, b in enumerate(bars):
        if i == 0:
            trs.append(b["h"] - b["l"])
        else:
            pc = bars[i - 1]["c"]
            trs.append(max(b["h"] - b["l"], abs(b["h"] - pc), abs(b["l"] - pc)))
    out, prev = [], None
    for i, tr in enumerate(trs):
        if i < length - 1:
            out.append(None)
            continue
        prev = sum(trs[:length]) / length if prev is None else (prev * (length - 1) + tr) / length
        out.append(prev)
    return out


def rsi(values, length):
    """Wilder RSI."""
    out = [None] * len(values)
    if len(values) <= length:
        return out
    gains = losses = 0.0
    for i in range(1, length + 1):
        d = values[i] - values[i - 1]
        gains += max(d, 0)
        losses += max(-d, 0)
    ag, al = gains / length, losses / length
    out[length] = 100.0 if al == 0 else 100 - 100 / (1 + ag / al)
    for i in range(length + 1, len(values)):
        d = values[i] - values[i - 1]
        ag = (ag * (length - 1) + max(d, 0)) / length
        al = (al * (length - 1) + max(-d, 0)) / length
        out[i] = 100.0 if al == 0 else 100 - 100 / (1 + ag / al)
    return out


def highest(values, length):
    """Highest of the `length` values BEFORE bar i (excludes bar i)."""
    return [None if i < length else max(values[i - length:i]) for i in range(len(values))]
