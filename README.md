# 株価・経済ダッシュボード

世界の株価チャート（テクニカル指標付き）・米国経済指標・経済ニュースを表示する個人用Streamlitアプリ。

## 機能

- **株価チャート**: 米・日・欧の主要銘柄（ローソク足）+ SMA / MACD / RSI
- **経済指標**: FRED の Tier1+2 指標（CPI, NFP, 失業率, FF金利, GDP, コアPCE, 小売売上高, PPI, 鉱工業生産, 10年債, VIX）
- **ニュース**: Finnhub の市場全体ニュース + 銘柄別ニュース

## セットアップ

1. APIキーを `.streamlit/secrets.toml` に記入
   - FRED: https://fred.stlouisfed.org/docs/api/api_key.html
   - Finnhub: https://finnhub.io/register
2. 依存ライブラリ（インストール済み）: `pip install -r requirements.txt`

## 起動

`run.bat` をダブルクリック、または:

```
python -m streamlit run app.py
```

ブラウザで http://localhost:8501 が開きます。

## 注意

- yfinance は非公式APIのため一時的に不安定になることがあります
- Finnhub 無料枠は 60回/分。銘柄ニュースは米国株中心（日本株は限定的）
