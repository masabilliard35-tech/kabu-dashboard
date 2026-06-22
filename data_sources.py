import datetime as dt
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime
from urllib.parse import quote

import pandas as pd
import requests
import streamlit as st
import yfinance as yf

FRED_BASE = "https://api.stlouisfed.org/fred/series/observations"
FRED_SERIES_RELEASE = "https://api.stlouisfed.org/fred/series/release"
FRED_RELEASE_DATES = "https://api.stlouisfed.org/fred/release/dates"
FINNHUB_BASE = "https://finnhub.io/api/v1"

# Tier1+2 経済指標（FRED series ID）
FRED_SERIES = {
    "Tier1": {
        "CPIAUCSL": "消費者物価指数 (CPI)",
        "PAYEMS": "非農業部門雇用者数 (NFP)",
        "UNRATE": "失業率",
        "DFEDTARU": "FOMC政策金利 (上限)",
        "GDPC1": "実質GDP",
    },
    "Tier2": {
        "PCEPILFE": "コアPCEデフレーター",
        "RSAFS": "小売売上高",
        "PPIACO": "生産者物価指数 (PPI)",
        "INDPRO": "鉱工業生産指数",
        "GACDISA066MSFRBNY": "製造業PMI代替 (NY連銀景況)",
        "GACDFSA066MSFRBPHI": "製造業PMI代替 (Philly連銀景況)",
    },
}

# カテゴリ別銘柄プリセット
TICKER_CATEGORIES = {
    "🇯🇵 日本株": {
        "トヨタ自動車 (7203)": "7203.T",
        "ソニーG (6758)": "6758.T",
        "キーエンス (6861)": "6861.T",
        "三菱UFJ FG (8306)": "8306.T",
        "ファーストリテイリング (9983)": "9983.T",
        "東京エレクトロン (8035)": "8035.T",
        "ソフトバンクG (9984)": "9984.T",
        "信越化学 (4063)": "4063.T",
        "任天堂 (7974)": "7974.T",
        "日立製作所 (6501)": "6501.T",
        "KDDI (9433)": "9433.T",
        "三菱商事 (8058)": "8058.T",
        "武田薬品 (4502)": "4502.T",
        "村田製作所 (6981)": "6981.T",
        "ホンダ (7267)": "7267.T",
        "三井住友FG (8316)": "8316.T",
        "リクルートHD (6098)": "6098.T",
        "デンソー (6902)": "6902.T",
        "NTT (9432)": "9432.T",
        "ファナック (6954)": "6954.T",
        "JR九州 (9142)": "9142.T",
    },
    "🇯🇵 日本指数": {
        "日経平均株価": "^N225",
        "TOPIX (1306・ETF)": "1306.T",
        "東証グロース250 (2516)": "2516.T",
    },
    "🇺🇸 米国株": {
        "Apple": "AAPL",
        "Microsoft": "MSFT",
        "NVIDIA": "NVDA",
        "Amazon": "AMZN",
        "Alphabet (Google)": "GOOGL",
        "Meta": "META",
        "Tesla": "TSLA",
        "Broadcom": "AVGO",
        "Berkshire Hathaway": "BRK-B",
        "JPMorgan": "JPM",
        "Visa": "V",
        "Eli Lilly": "LLY",
        "UnitedHealth": "UNH",
        "Exxon Mobil": "XOM",
        "Johnson & Johnson": "JNJ",
        "Procter & Gamble": "PG",
        "Coca-Cola": "KO",
        "Walmart": "WMT",
        "AMD": "AMD",
        "Netflix": "NFLX",
    },
    "🇺🇸 米国 株価指数先物": {
        "S&P500先物 (ES)": "ES=F",
        "NASDAQ100先物 (NQ)": "NQ=F",
        "ダウ先物 (YM)": "YM=F",
        "ラッセル2000先物 (RTY)": "RTY=F",
        "VIX (^VIX)": "^VIX",
    },
    "🇺🇸 米国 セクターETF": {
        "情報技術 (XLK)": "XLK",
        "金融 (XLF)": "XLF",
        "エネルギー (XLE)": "XLE",
        "ヘルスケア (XLV)": "XLV",
        "一般消費財 (XLY)": "XLY",
        "生活必需品 (XLP)": "XLP",
        "資本財 (XLI)": "XLI",
        "素材 (XLB)": "XLB",
        "公益事業 (XLU)": "XLU",
        "不動産 (XLRE)": "XLRE",
        "通信サービス (XLC)": "XLC",
        "半導体 (SOXX)": "SOXX",
        "製薬 (PPH)": "PPH",
        "原子力 (NLR)": "NLR",
        "金鉱株 (GDX)": "GDX",
    },
    "🇺🇸 米国 債券ETF": {
        "米国債20年 (TLT)": "TLT",
        "米国債20年3倍 (TMF)": "TMF",
        "米10年債利回り (^TNX)": "^TNX",
    },
    "🌍 国別ETF": {
        "日本 (EWJ)": "EWJ",
        "中国 (MCHI)": "MCHI",
        "中国大型 (FXI)": "FXI",
        "インド (INDA)": "INDA",
        "インドネシア (EIDO)": "EIDO",
        "マレーシア (EWM)": "EWM",
        "タイ (THD)": "THD",
        "欧州 (VGK)": "VGK",
        "英国 (EWU)": "EWU",
        "ドイツ (EWG)": "EWG",
        "ポーランド (EPOL)": "EPOL",
        "トルコ (TUR)": "TUR",
        "ブラジル (EWZ)": "EWZ",
        "メキシコ (EWW)": "EWW",
        "韓国 (EWY)": "EWY",
        "台湾 (EWT)": "EWT",
        "豪州 (EWA)": "EWA",
        "太平洋除く日本 (EPP)": "EPP",
        "カナダ (EWC)": "EWC",
        "南アフリカ (EZA)": "EZA",
        "新興国 (VWO)": "VWO",
    },
    "🛢 コモディティ": {
        "金 (Gold)": "GC=F",
        "銀 (Silver)": "SI=F",
        "プラチナ": "PL=F",
        "パラジウム": "PA=F",
        "WTI原油": "CL=F",
        "ブレント原油": "BZ=F",
        "天然ガス": "NG=F",
        "銅 (Copper)": "HG=F",
        "小麦 (Wheat)": "ZW=F",
        "トウモロコシ (Corn)": "ZC=F",
        "大豆 (Soybean)": "ZS=F",
    },
    "₿ 仮想通貨": {
        "Bitcoin (BTC)": "BTC-USD",
        "Ethereum (ETH)": "ETH-USD",
        "XRP": "XRP-USD",
        "Solana (SOL)": "SOL-USD",
        "BNB": "BNB-USD",
        "Dogecoin (DOGE)": "DOGE-USD",
        "Cardano (ADA)": "ADA-USD",
        "Avalanche (AVAX)": "AVAX-USD",
    },
    "💱 FX": {
        "米ドル/円": "USDJPY=X",
        "ユーロ/円": "EURJPY=X",
        "英ポンド/円": "GBPJPY=X",
        "豪ドル/円": "AUDJPY=X",
        "ユーロ/米ドル": "EURUSD=X",
        "英ポンド/米ドル": "GBPUSD=X",
        "豪ドル/米ドル": "AUDUSD=X",
        "米ドル/スイスフラン": "USDCHF=X",
        "南アランド/円": "ZARJPY=X",
        "トルコリラ/円": "TRYJPY=X",
    },
}


# ウォッチリストの表示順
CATEGORY_ORDER = [
    "🇺🇸 米国 株価指数先物",
    "🇺🇸 米国 セクターETF",
    "🇺🇸 米国 債券ETF",
    "🇯🇵 日本指数",
    "🌍 国別ETF",
    "🛢 コモディティ",
    "₿ 仮想通貨",
    "💱 FX",
    "🇺🇸 米国株",
    "🇯🇵 日本株",
]


def is_us_equity(ticker: str) -> bool:
    """company-news が使える米国株/ETFか（記号付きシンボルを除外）"""
    bad = ("=", "^", ".")
    return not any(c in ticker for c in bad) and not ticker.endswith("-USD")


@st.cache_data(ttl=300)
def fetch_quotes(symbols: tuple) -> dict:
    """複数銘柄の現在値・変動・変動率を一括取得"""
    data = yf.download(
        list(symbols),
        period="5d",
        interval="1d",
        auto_adjust=True,
        progress=False,
        group_by="ticker",
        threads=True,
    )
    out = {}
    for s in symbols:
        try:
            closes = data[s]["Close"].dropna()
            if len(closes) >= 2:
                last, prev = float(closes.iloc[-1]), float(closes.iloc[-2])
                out[s] = (last, last - prev, (last / prev - 1) * 100)
            elif len(closes) == 1:
                out[s] = (float(closes.iloc[-1]), 0.0, 0.0)
            else:
                out[s] = None
        except Exception:
            out[s] = None
    return out


@st.cache_data(ttl=300)
def fetch_stock(ticker: str, period: str, interval: str) -> pd.DataFrame:
    df = yf.download(
        ticker,
        period=period,
        interval=interval,
        auto_adjust=True,
        progress=False,
    )
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    return df


@st.cache_data(ttl=3600)
def fetch_fred(series_id: str, api_key: str, start: str) -> pd.DataFrame:
    params = {
        "series_id": series_id,
        "api_key": api_key,
        "file_type": "json",
        "observation_start": start,
    }
    r = requests.get(FRED_BASE, params=params, timeout=15)
    r.raise_for_status()
    obs = r.json().get("observations", [])
    rows = [
        (o["date"], float(o["value"]))
        for o in obs
        if o["value"] not in (".", "")
    ]
    df = pd.DataFrame(rows, columns=["date", "value"])
    df["date"] = pd.to_datetime(df["date"])
    return df.set_index("date")


@st.cache_data(ttl=86400)
def fetch_next_release(series_id: str, api_key: str):
    """指標の次回発表予定日（今日以降で最も近い日）を返す"""
    r = requests.get(
        FRED_SERIES_RELEASE,
        params={"series_id": series_id, "api_key": api_key, "file_type": "json"},
        timeout=15,
    )
    r.raise_for_status()
    rid = r.json()["releases"][0]["id"]
    r2 = requests.get(
        FRED_RELEASE_DATES,
        params={
            "release_id": rid,
            "api_key": api_key,
            "file_type": "json",
            "include_release_dates_with_no_data": "true",
            "realtime_end": "9999-12-31",
            "sort_order": "asc",
            "limit": 1000,
        },
        timeout=15,
    )
    r2.raise_for_status()
    today = dt.date.today().isoformat()
    future = [
        d["date"] for d in r2.json().get("release_dates", []) if d["date"] >= today
    ]
    return min(future) if future else None


@st.cache_data(ttl=600)
def fetch_jp_news(query: str, limit: int = 25, lang: str = "ja") -> list:
    """Google News RSS からニュースを取得（APIキー不要、lang=ja/en）"""
    loc = (
        "&hl=en-US&gl=US&ceid=US:en" if lang == "en"
        else "&hl=ja&gl=JP&ceid=JP:ja"
    )
    url = "https://news.google.com/rss/search?q=" + quote(query) + loc
    r = requests.get(url, timeout=15, headers={"User-Agent": "Mozilla/5.0"})
    r.raise_for_status()
    root = ET.fromstring(r.content)
    out = []
    for it in root.findall(".//item"):
        out.append({
            "title": it.findtext("title", ""),
            "link": it.findtext("link", ""),
            "pub": it.findtext("pubDate", ""),
            "source": it.findtext("source", ""),
        })

    def _ts(n):
        try:
            return parsedate_to_datetime(n["pub"])
        except Exception:
            return dt.datetime(1970, 1, 1, tzinfo=dt.timezone.utc)

    out.sort(key=_ts, reverse=True)
    return out[:limit]


@st.cache_data(ttl=600)
def fetch_market_news(api_key: str, category: str = "general") -> list:
    r = requests.get(
        f"{FINNHUB_BASE}/news",
        params={"category": category, "token": api_key},
        timeout=15,
    )
    r.raise_for_status()
    return r.json()


@st.cache_data(ttl=600)
def fetch_company_news(ticker: str, api_key: str, days: int = 14) -> list:
    today = dt.date.today()
    frm = today - dt.timedelta(days=days)
    r = requests.get(
        f"{FINNHUB_BASE}/company-news",
        params={
            "symbol": ticker,
            "from": frm.isoformat(),
            "to": today.isoformat(),
            "token": api_key,
        },
        timeout=15,
    )
    r.raise_for_status()
    return r.json()
