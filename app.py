import datetime as dt

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots
from streamlit_js_eval import streamlit_js_eval

import indicators as ind
import signals as sg
from data_sources import (
    CATEGORY_ORDER,
    FRED_SERIES,
    TICKER_CATEGORIES,
    fetch_fred,
    fetch_history_bulk,
    fetch_next_release,
    fetch_quotes,
    fetch_stock,
)

st.set_page_config(
    page_title="株価・経済ダッシュボード",
    layout="wide",
    initial_sidebar_state="collapsed",
)

UP = "#26a69a"
DOWN = "#ef5350"

st.markdown(
    """
    <style>
    .block-container {padding: 0.6rem 0.6rem 0.4rem 0.6rem; max-width: 100% !important;}
    h3, h4 {margin: 0.2rem 0;}
    section[data-testid="stSidebar"] {display: none;}
    div[data-testid="stHorizontalBlock"] {gap: 0.4rem;}
    .wl-table {width: 100%; border-collapse: collapse; font-size: 0.72rem;
               table-layout: fixed;}
    .wl-table td {padding: 0px 3px; white-space: nowrap; line-height: 1.5;
                  overflow: hidden; text-overflow: ellipsis;}
    .wl-table tr:hover {background: rgba(125,125,125,0.12);}
    .wl-table a {text-decoration: none; color: #3d9df6; font-weight: 600;}
    .wl-cat {font-weight: 700; color: #888; padding-top: 5px !important;
             border-bottom: 1px solid rgba(125,125,125,0.25);}
    .wl-table .num {text-align: right; font-variant-numeric: tabular-nums;}
    .wl-head td {font-weight: 700; color: #aaa;
                 border-bottom: 1px solid rgba(125,125,125,0.4);}
    .upc {font-size: 0.70rem; line-height: 1.5;}
    .ind-set div[data-testid="stNumberInput"] input,
    .ind-set div[data-testid="stSelectbox"] div {font-size: 0.66rem;}
    div[data-testid="stNumberInput"] input {padding: 2px 6px;}
    /* チャート周りの余白を詰める */
    div[data-testid="stVerticalBlock"] {gap: 0.3rem;}
    div[data-testid="stPlotlyChart"] {margin: 0 !important;}
    div[data-testid="stElementContainer"] {margin-bottom: 0 !important;}
    .sc-table {width: 100%; border-collapse: collapse; font-size: 0.82rem;}
    .sc-table td, .sc-table th {padding: 3px 8px; text-align: left;
                  border-bottom: 1px solid rgba(125,125,125,0.18);}
    .sc-table th {color: #aaa; border-bottom: 1px solid rgba(125,125,125,0.4);}
    .sc-table a {text-decoration: none; color: #3d9df6; font-weight: 600;}
    .sc-table tr:hover {background: rgba(125,125,125,0.10);}
    </style>
    """,
    unsafe_allow_html=True,
)

FRED_KEY = st.secrets.get("FRED_API_KEY", "")
today = dt.date.today()

SYM_TO_LABEL = {
    s: l for c in TICKER_CATEGORIES for l, s in TICKER_CATEGORIES[c].items()
}
ALL_FRED = {sid: label for m in FRED_SERIES.values() for sid, label in m.items()}
ALL_SYMS = tuple(
    sym for cat in CATEGORY_ORDER for sym in TICKER_CATEGORIES[cat].values()
)


def sym_href(sym: str) -> str:
    return "?sym=" + sym.replace("=", "%3D").replace("^", "%5E")


if "ticker" not in st.session_state:
    st.session_state.ticker = "AAPL"
qp_sym = st.query_params.get("sym")
if qp_sym:
    st.session_state.ticker = qp_sym

# ブラウザの高さに合わせてチャート高を決定（RSIまで画面内に収める）
vh = streamlit_js_eval(js_expressions="window.innerHeight", key="VH")
chart_h = max(420, int((vh or 850) - 200))

tab_dash, tab_screen = st.tabs(["📊 ダッシュボード", "🔍 スクリーニング"])

# ============================================================
# タブ1: ダッシュボード
# ============================================================
with tab_dash:
    left_col, main_col, right_col = st.columns([1.35, 4.3, 1.15])

    # ---- 右: ウォッチリスト ----
    with right_col:
        st.markdown("##### ウォッチリスト")
        try:
            quotes = fetch_quotes(ALL_SYMS)
        except Exception:
            quotes = {}

        html = ["<table class='wl-table'>"]
        html.append(
            "<colgroup><col style='width:27%'><col style='width:27%'>"
            "<col style='width:23%'><col style='width:23%'></colgroup>"
        )
        html.append(
            "<tr class='wl-head'><td>銘柄</td><td class='num'>現在値</td>"
            "<td class='num'>変動</td><td class='num'>変動率</td></tr>"
        )
        for cat in CATEGORY_ORDER:
            rows_html = []
            for label, sym in TICKER_CATEGORIES[cat].items():
                q = quotes.get(sym)
                if not q:
                    continue
                last, chg, pct = q
                col = UP if chg >= 0 else DOWN
                link = (
                    f"<a href='{sym_href(sym)}' target='_self' "
                    f"title='{label}'>{sym}</a>"
                )
                rows_html.append(
                    f"<tr><td>{link}</td>"
                    f"<td class='num' style='color:{col}'>{last:,.2f}</td>"
                    f"<td class='num' style='color:{col}'>{chg:+,.2f}</td>"
                    f"<td class='num' style='color:{col}'>{pct:+.2f}%</td></tr>"
                )
            if rows_html:
                html.append(
                    f"<tr><td colspan='4' class='wl-cat'>{cat}</td></tr>"
                )
                html.extend(rows_html)
        html.append("</table>")

        with st.container(height=chart_h + 90):
            st.markdown("".join(html), unsafe_allow_html=True)

    # ---- 中央: 設定バー + チャート ----
    with main_col:
        show_sma = show_boll = show_vol = show_macd = show_rsi = True

        for k, v in {"sma_short": 25, "sma_long": 75,
                     "boll_period": 20, "macd_set": "12 / 26 / 9"}.items():
            st.session_state.setdefault(k, v)
        st.session_state.setdefault(
            "sig_sel", ["ゴールデン/デッドクロス", "MACDクロス"]
        )
        sma_short = st.session_state.sma_short
        sma_long = st.session_state.sma_long
        boll_period = st.session_state.boll_period
        macd_set = st.session_state.macd_set
        macd_fast, macd_slow, macd_sig = (
            (12, 26, 9) if macd_set.startswith("12") else (9, 18, 6)
        )

        ticker = st.session_state.ticker
        name = SYM_TO_LABEL.get(ticker, ticker)
        tn = st.columns([3.5, 1, 1.3])
        tn[0].markdown(
            f"#### {name}　<small>{ticker}</small>", unsafe_allow_html=True
        )
        interval = tn[1].selectbox(
            "足", ["1d", "1wk", "1mo"], index=0, label_visibility="collapsed",
        )
        period = tn[2].selectbox(
            "表示期間", ["1mo", "3mo", "6mo", "1y", "2y", "5y", "max"], index=2,
        )

        try:
            buffer = {"1mo": "1y", "3mo": "2y", "6mo": "3y", "1y": "5y",
                      "2y": "10y", "5y": "max", "max": "max"}
            df = fetch_stock(ticker, buffer.get(period, period), interval)
            if df.empty:
                st.error("データを取得できませんでした。ティッカーを確認してください。")
            else:
                close = df["Close"]
                has_vol = (
                    show_vol and "Volume" in df and df["Volume"].fillna(0).sum() > 0
                )

                weights = [0.60]
                ridx = 1
                vol_row = macd_row = rsi_row = None
                if has_vol:
                    ridx += 1
                    vol_row = ridx
                    weights.append(0.13)
                if show_macd:
                    ridx += 1
                    macd_row = ridx
                    weights.append(0.135)
                if show_rsi:
                    ridx += 1
                    rsi_row = ridx
                    weights.append(0.135)
                total = sum(weights)
                heights = [w / total for w in weights]
                rows = len(weights)

                fig = make_subplots(
                    rows=rows, cols=1, shared_xaxes=True,
                    vertical_spacing=0.02, row_heights=heights,
                )

                def panel_label(text, row):
                    fig.add_annotation(
                        text=text, xref="x domain", yref="y domain",
                        x=0.004, y=0.97, xanchor="left", yanchor="top",
                        showarrow=False, font=dict(size=11, color="#bbb"),
                        row=row, col=1,
                    )

                fig.add_trace(
                    go.Candlestick(
                        x=df.index, open=df["Open"], high=df["High"],
                        low=df["Low"], close=df["Close"], name="価格",
                        increasing_line_color=UP, decreasing_line_color=DOWN,
                        hoverinfo="skip",
                    ),
                    row=1, col=1,
                )
                fig.add_trace(
                    go.Scatter(
                        x=df.index, y=close, mode="lines",
                        line=dict(width=0), opacity=0, showlegend=False,
                        name="",
                        hovertemplate="%{x|%Y-%m-%d}<br>%{y:,.2f}<extra></extra>",
                    ),
                    row=1, col=1,
                )
                if show_sma:
                    fig.add_trace(
                        go.Scatter(x=df.index, y=ind.sma(close, sma_short),
                                   name=f"SMA{sma_short}", hoverinfo="skip",
                                   line=dict(width=1, color="#f5c542")),
                        row=1, col=1,
                    )
                    fig.add_trace(
                        go.Scatter(x=df.index, y=ind.sma(close, sma_long),
                                   name=f"SMA{sma_long}", hoverinfo="skip",
                                   line=dict(width=1, color="#42a5f5")),
                        row=1, col=1,
                    )
                if show_boll:
                    up, mid, low = ind.bollinger(close, boll_period)
                    fig.add_trace(
                        go.Scatter(x=df.index, y=up, name="BB上", hoverinfo="skip",
                                   line=dict(width=1, color="rgba(180,180,210,0.6)")),
                        row=1, col=1,
                    )
                    fig.add_trace(
                        go.Scatter(x=df.index, y=low, name="BB下", hoverinfo="skip",
                                   line=dict(width=1, color="rgba(180,180,210,0.6)"),
                                   fill="tonexty",
                                   fillcolor="rgba(150,150,200,0.08)"),
                        row=1, col=1,
                    )

                if has_vol:
                    vcolors = [
                        "rgba(38,166,154,0.6)" if c >= o else "rgba(239,83,80,0.6)"
                        for o, c in zip(df["Open"], df["Close"])
                    ]
                    fig.add_trace(
                        go.Bar(x=df.index, y=df["Volume"], name="出来高",
                               marker_color=vcolors, marker_line_width=0,
                               hoverinfo="skip"),
                        row=vol_row, col=1,
                    )
                    panel_label("出来高", vol_row)

                if show_macd:
                    macd_line, signal_line, hist = ind.macd(
                        close, macd_fast, macd_slow, macd_sig
                    )
                    fig.add_trace(
                        go.Bar(x=df.index, y=hist, name="MACD Hist",
                               marker_color="gray", hoverinfo="skip"),
                        row=macd_row, col=1,
                    )
                    fig.add_trace(
                        go.Scatter(x=df.index, y=macd_line, name="MACD",
                                   hoverinfo="skip",
                                   line=dict(width=1, color="#42a5f5")),
                        row=macd_row, col=1,
                    )
                    fig.add_trace(
                        go.Scatter(x=df.index, y=signal_line, name="Signal",
                                   hoverinfo="skip",
                                   line=dict(width=1, color="#ff7043")),
                        row=macd_row, col=1,
                    )
                    panel_label(
                        f"MACD {macd_fast}/{macd_slow}/{macd_sig}", macd_row
                    )

                if show_rsi:
                    fig.add_trace(
                        go.Scatter(x=df.index, y=ind.rsi(close), name="RSI",
                                   hovertemplate="RSI %{y:.1f}<extra></extra>",
                                   line=dict(width=1, color="#ab47bc")),
                        row=rsi_row, col=1,
                    )
                    fig.add_hline(y=70, line_dash="dash", line_color="red",
                                  row=rsi_row, col=1)
                    fig.add_hline(y=30, line_dash="dash", line_color="green",
                                  row=rsi_row, col=1)
                    panel_label("RSI", rsi_row)

                range_days = {"1mo": 30, "3mo": 91, "6mo": 182, "1y": 365,
                              "2y": 730, "5y": 1825, "max": None}
                d = range_days.get(period)
                vis = (
                    df[df.index >= (df.index[-1] - pd.Timedelta(days=d))]
                    if d else df
                )
                if d and not vis.empty:
                    xmax = df.index[-1] + pd.Timedelta(days=3)
                    fig.update_xaxes(range=[vis.index[0], xmax])
                base = vis if not vis.empty else df

                lo = float(base["Low"].min())
                hi = float(base["High"].max())

                # シグナル矢印
                sig_groups = st.session_state.get("sig_sel", [])
                if sig_groups:
                    cols = [c for g in sig_groups for c in sg.GROUPS.get(g, [])]
                    sdf = sg.compute(df, sma_short, sma_long, macd_fast,
                                     macd_slow, macd_sig, boll_period)
                    rng = (hi - lo) or hi or 1.0
                    off = rng * 0.03
                    bx, by, bt = [], [], []
                    sx, sy, stt = [], [], []
                    for c in cols:
                        label, direction = sg.SIGNAL_META[c]
                        hit = sdf.index[sdf[c].fillna(False)].intersection(base.index)
                        for ts in hit:
                            if direction == "buy":
                                bx.append(ts)
                                by.append(float(df.loc[ts, "Low"]) - off)
                                bt.append(label)
                            else:
                                sx.append(ts)
                                sy.append(float(df.loc[ts, "High"]) + off)
                                stt.append(label)
                    if bx:
                        fig.add_trace(
                            go.Scatter(
                                x=bx, y=by, mode="markers", text=bt,
                                marker=dict(symbol="triangle-up", size=11,
                                            color=UP,
                                            line=dict(width=0.5, color="white")),
                                hovertemplate="%{text} 買い<extra></extra>",
                                name="買い"),
                            row=1, col=1,
                        )
                        lo = min(lo, min(by) - off)
                    if sx:
                        fig.add_trace(
                            go.Scatter(
                                x=sx, y=sy, mode="markers", text=stt,
                                marker=dict(symbol="triangle-down", size=11,
                                            color=DOWN,
                                            line=dict(width=0.5, color="white")),
                                hovertemplate="%{text} 売り<extra></extra>",
                                name="売り"),
                            row=1, col=1,
                        )
                        hi = max(hi, max(sy) + off)

                pad = (hi - lo) * 0.05 or hi * 0.05
                fig.update_yaxes(range=[lo - pad, hi + pad], side="right",
                                 row=1, col=1)
                if has_vol:
                    vv = float(base["Volume"].max())
                    fig.update_yaxes(range=[0, vv * 1.1], showticklabels=False,
                                     showgrid=False, row=vol_row, col=1)
                if show_macd:
                    fig.update_yaxes(showticklabels=True, side="right",
                                     row=macd_row, col=1)
                if show_rsi:
                    fig.update_yaxes(range=[0, 100], showticklabels=True,
                                     side="right", row=rsi_row, col=1)

                if interval == "1d" and not ticker.endswith("-USD"):
                    fig.update_xaxes(rangebreaks=[dict(bounds=["sat", "mon"])])

                fig.update_xaxes(
                    showspikes=True, spikemode="across", spikesnap="cursor",
                    spikethickness=1, spikedash="dot", spikecolor="#999",
                )
                fig.update_yaxes(
                    showspikes=True, spikethickness=1, spikedash="dot",
                    spikecolor="#999",
                )
                fig.update_layout(
                    height=chart_h,
                    template="plotly_dark",
                    xaxis_rangeslider_visible=False,
                    hovermode="x",
                    showlegend=False,
                    dragmode="pan",
                    margin=dict(t=2, b=2, l=6, r=6),
                    bargap=0.05,
                )
                st.plotly_chart(fig, use_container_width=True,
                                config={"scrollZoom": True, "displaylogo": False})
        except Exception as e:
            st.error(f"取得エラー: {e}")

        # 指標・シグナル設定（チャート直下・小型）
        st.markdown("<div class='ind-set'>", unsafe_allow_html=True)
        iset = st.columns([1, 1, 1, 1.6, 2.4])
        iset[0].number_input("SMA短", 5, 200, key="sma_short")
        iset[1].number_input("SMA長", 5, 400, key="sma_long")
        iset[2].number_input("BB期間", 5, 100, key="boll_period")
        iset[3].selectbox("MACD (短/長/信号)", ["12 / 26 / 9", "9 / 18 / 6"],
                          key="macd_set")
        iset[4].multiselect("シグナル矢印", list(sg.GROUPS), key="sig_sel")
        st.markdown("</div>", unsafe_allow_html=True)

    # ---- 左: 経済指標 ----
    with left_col:
        st.markdown("##### 🏦 経済指標")
        if not FRED_KEY:
            st.info("FRED_API_KEY 未設定")
        else:
            upcoming = []
            for m in FRED_SERIES.values():
                for sid_, label in m.items():
                    try:
                        nd = fetch_next_release(sid_, FRED_KEY)
                        if nd:
                            days = (dt.date.fromisoformat(nd) - today).days
                            upcoming.append((nd, label, days))
                    except Exception:
                        pass
            upcoming.sort()
            st.markdown("<b>📅 次回発表予定</b>", unsafe_allow_html=True)
            lines = []
            for nd, label, days in upcoming[:6]:
                tag = "🔔" if 0 <= days <= 7 else "・"
                lines.append(f"{tag} {label}: {nd}（あと{days}日）")
            st.markdown(
                "<div class='upc'>" + "<br>".join(lines) + "</div>",
                unsafe_allow_html=True,
            )
            st.markdown("---")
            sid = st.selectbox("指標を選択", list(ALL_FRED),
                               format_func=lambda s: ALL_FRED[s])
            try:
                start = (today - dt.timedelta(days=365 * 7)).isoformat()
                edf = fetch_fred(sid, FRED_KEY, start)
                if not edf.empty:
                    lv = float(edf["value"].iloc[-1])

                    def pct_since(days):
                        t = edf.index[-1] - pd.Timedelta(days=days)
                        past = edf[edf.index <= t]
                        if past.empty:
                            return None
                        base_v = float(past["value"].iloc[-1])
                        return (lv / base_v - 1) * 100 if base_v else None

                    mom = pct_since(30)
                    yoy = pct_since(365)
                    st.metric(ALL_FRED[sid], f"{lv:,.2f}")
                    parts = []
                    if mom is not None:
                        c = UP if mom >= 0 else DOWN
                        parts.append(
                            f"<span style='color:{c}'>前月比 {mom:+.2f}%</span>"
                        )
                    if yoy is not None:
                        c = UP if yoy >= 0 else DOWN
                        parts.append(
                            f"<span style='color:{c}'>前年比 {yoy:+.2f}%</span>"
                        )
                    st.markdown(
                        "<div style='font-size:0.78rem; font-weight:600; "
                        "margin:4px 0 12px 0;'>" + " ／ ".join(parts)
                        + "</div>", unsafe_allow_html=True,
                    )
                    vals = edf["value"].iloc[-36:]
                    vmin, vmax = float(vals.min()), float(vals.max())
                    m = (vmax - vmin) * 0.12 or abs(vmax) * 0.05 or 1
                    bar = go.Figure(
                        go.Bar(x=vals.index, y=vals, marker_color="#42a5f5")
                    )
                    bar.update_layout(
                        height=200, template="plotly_dark",
                        margin=dict(t=4, b=4, l=6, r=6), showlegend=False,
                        yaxis=dict(range=[vmin - m, vmax + m]),
                    )
                    st.plotly_chart(bar, use_container_width=True,
                                    config={"displaylogo": False})
            except Exception as e:
                st.write(f"取得エラー: {e}")

# ============================================================
# タブ2: スクリーニング
# ============================================================
with tab_screen:
    st.markdown("##### 🔍 今日のシグナル スクリーニング")
    st.caption(
        "全銘柄を日足でスキャンし、直近で出た売買シグナルを抽出します。"
        "（SMA 25/75・MACD 12/26/9・RSI 14・BB 20）"
    )
    cc = st.columns([1.2, 1.2, 4])
    span_label = cc[0].selectbox("対象期間", ["最新日のみ", "直近3日", "直近5日"],
                                 index=1)
    span_n = {"最新日のみ": 1, "直近3日": 3, "直近5日": 5}[span_label]
    run = cc[1].button("🔄 スキャン実行", type="primary")

    if run:
        with st.spinner("全銘柄をスキャン中…（初回は20〜40秒）"):
            try:
                hist = fetch_history_bulk(ALL_SYMS, "1y")
            except Exception as e:
                hist = {}
                st.error(f"取得エラー: {e}")
            results = []
            for cat in CATEGORY_ORDER:
                for label, sym in TICKER_CATEGORIES[cat].items():
                    d = hist.get(sym)
                    if d is None or "Close" not in d or len(d.dropna()) < 80:
                        continue
                    sdf = sg.compute(d)
                    recent = sdf.iloc[-span_n:]
                    for c in sg.SIGNAL_META:
                        col = recent[c].fillna(False)
                        if col.any():
                            ts = col.index[col][-1]
                            _, direction = sg.SIGNAL_META[c]
                            results.append({
                                "date": ts.date().isoformat(),
                                "sym": sym, "label": label,
                                "sig": sg.SIGNAL_FULL[c], "dir": direction,
                            })
            st.session_state.scan_results = results
            st.session_state.scan_time = dt.datetime.now().strftime("%m/%d %H:%M")

    results = st.session_state.get("scan_results")
    if results is None:
        st.info("「スキャン実行」を押すと、全銘柄の売買シグナルを一覧表示します。")
    else:
        st.caption(f"スキャン時刻: {st.session_state.get('scan_time', '-')}　"
                   f"検出 {len(results)} 件")

        def render(items, title, color):
            rows = sorted(items, key=lambda r: r["date"], reverse=True)
            h = [f"<h5 style='color:{color};margin:6px 0'>{title}（{len(rows)}）</h5>"]
            h.append("<table class='sc-table'><tr><th>日付</th><th>銘柄</th>"
                     "<th>シグナル</th></tr>")
            for r in rows:
                link = (f"<a href='{sym_href(r['sym'])}' target='_self' "
                        f"title='{r['label']}'>{r['sym']}</a>")
                h.append(f"<tr><td>{r['date']}</td><td>{link}</td>"
                         f"<td>{r['sig']}</td></tr>")
            h.append("</table>")
            st.markdown("".join(h), unsafe_allow_html=True)

        buys = [r for r in results if r["dir"] == "buy"]
        sells = [r for r in results if r["dir"] == "sell"]
        sc = st.columns(2)
        with sc[0]:
            render(buys, "▲ 買いシグナル", UP)
        with sc[1]:
            render(sells, "▼ 売りシグナル", DOWN)
        st.caption("銘柄をクリックすると、ダッシュボードのチャートに切り替わります。")
