import pandas as pd

import indicators as ind

SIGNAL_META = {
    "gc": ("GC", "buy"),
    "dc": ("DC", "sell"),
    "macd_buy": ("MACD↑", "buy"),
    "macd_sell": ("MACD↓", "sell"),
    "rsi_buy": ("RSI↑", "buy"),
    "rsi_sell": ("RSI↓", "sell"),
    "bb_buy": ("BB↑", "buy"),
    "bb_sell": ("BB↓", "sell"),
}

SIGNAL_FULL = {
    "gc": "ゴールデンクロス",
    "dc": "デッドクロス",
    "macd_buy": "MACD買い転換",
    "macd_sell": "MACD売り転換",
    "rsi_buy": "RSI売られすぎ脱出",
    "rsi_sell": "RSI買われすぎ転落",
    "bb_buy": "BB下限から反発",
    "bb_sell": "BB上限から下落",
}

GROUPS = {
    "ゴールデン/デッドクロス": ["gc", "dc"],
    "MACDクロス": ["macd_buy", "macd_sell"],
    "RSI": ["rsi_buy", "rsi_sell"],
    "ボリンジャー": ["bb_buy", "bb_sell"],
}


def _cross_up(a, b):
    return (a > b) & (a.shift(1) <= b.shift(1))


def _cross_down(a, b):
    return (a < b) & (a.shift(1) >= b.shift(1))


def compute(df, sma_short=25, sma_long=75, macd_fast=12, macd_slow=26,
            macd_sig=9, boll_period=20, rsi_period=14):
    close = df["Close"]
    out = pd.DataFrame(index=df.index)

    s = ind.sma(close, sma_short)
    l = ind.sma(close, sma_long)
    out["gc"] = _cross_up(s, l)
    out["dc"] = _cross_down(s, l)

    macd_line, signal_line, _ = ind.macd(close, macd_fast, macd_slow, macd_sig)
    out["macd_buy"] = _cross_up(macd_line, signal_line)
    out["macd_sell"] = _cross_down(macd_line, signal_line)

    r = ind.rsi(close, rsi_period)
    thirty = pd.Series(30.0, index=r.index)
    seventy = pd.Series(70.0, index=r.index)
    out["rsi_buy"] = _cross_up(r, thirty)
    out["rsi_sell"] = _cross_down(r, seventy)

    up, mid, low = ind.bollinger(close, boll_period)
    out["bb_buy"] = _cross_up(close, low)
    out["bb_sell"] = _cross_down(close, up)

    return out
