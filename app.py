import datetime as dt
import time

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import yfinance as yf

st.set_page_config(page_title="台股每日 KD 追蹤", page_icon="📈", layout="wide")

DEFAULT_STOCKS = {
    "006208": "富邦台50",
    "00900": "富邦特選高股息30",
    "00929": "復華台灣科技優息",
    "00941": "中信上游半導體",
    "2884": "玉山金",
    "2887": "台新新光金（請確認代號資料）",
    "2892": "第一金",
    "4118": "自行確認公司名稱／市場",
}

st.title("📈 台股庫存每日 KD 追蹤")
st.caption("以日線收盤資料計算 KD(9,3,3)；預設觀察黃金交叉、死亡交叉，以及 K/D 低於 20 或高於 80。")

with st.sidebar:
    st.header("設定")
    codes_text = st.text_area(
        "股票代號（逗號或換行分隔）",
        value="006208,00900,00929,00941,2884,2887,2892,4118",
        height=110,
    )
    period = st.selectbox("歷史資料期間", ["6mo", "1y", "2y", "5y"], index=1)
    show_chart = st.checkbox("顯示個股 KD 走勢圖", value=True)
    st.markdown("---")
    st.markdown("**資料來源**：Yahoo Finance（由 yfinance 套件讀取）。")
    st.caption("資料可能延遲、缺漏或因代號變更而無法取得；本工具不是券商報價系統。")

def parse_codes(text):
    raw = text.replace("\n", ",").replace("，", ",").split(",")
    return list(dict.fromkeys(x.strip() for x in raw if x.strip()))

def get_history(code, period):
    # 台股上市通常使用 .TW；上櫃通常使用 .TWO。依序嘗試兩種代碼。
    candidates = [f"{code}.TW", f"{code}.TWO"]
    errors = []
    for ticker in candidates:
        try:
            data = yf.Ticker(ticker).history(period=period, auto_adjust=False, actions=False)
            if data is not None and not data.empty and {"High", "Low", "Close"}.issubset(data.columns):
                data = data[["High", "Low", "Close"]].copy()
                data.index = pd.to_datetime(data.index).tz_localize(None)
                data = data[~data.index.duplicated(keep="last")].sort_index()
                # 排除沒有有效 OHLC 的列
                data = data.dropna(subset=["High", "Low", "Close"])
                if len(data) >= 12:
                    return data, ticker, None
                errors.append(f"{ticker}: 歷史資料不足")
            else:
                errors.append(f"{ticker}: 查無資料")
        except Exception as e:
            errors.append(f"{ticker}: {type(e).__name__}")
        time.sleep(0.15)
    return None, None, "；".join(errors)

def calculate_kd(data):
    df = data.copy()
    low_n = df["Low"].rolling(9, min_periods=9).min()
    high_n = df["High"].rolling(9, min_periods=9).max()
    spread = high_n - low_n
    rsv = ((df["Close"] - low_n) / spread.replace(0, pd.NA) * 100).fillna(50.0)
    # 常見 KD(9,3,3) 遞迴平滑：初始 K、D = 50
    k_values, d_values = [], []
    k_prev = d_prev = 50.0
    for value in rsv:
        if pd.isna(value):
            k = k_prev
        else:
            k = (2 / 3) * k_prev + (1 / 3) * float(value)
        d = (2 / 3) * d_prev + (1 / 3) * k
        k_values.append(k)
        d_values.append(d)
        k_prev, d_prev = k, d
    df["K"] = k_values
    df["D"] = d_values
    df["RSV"] = rsv
    return df

def get_signal(df):
    if len(df) < 2:
        return "資料不足"
    prev, cur = df.iloc[-2], df.iloc[-1]
    signals = []
    if prev["K"] <= prev["D"] and cur["K"] > cur["D"]:
        signals.append("黃金交叉")
    elif prev["K"] >= prev["D"] and cur["K"] < cur["D"]:
        signals.append("死亡交叉")
    if cur["K"] < 20 or cur["D"] < 20:
        signals.append("KD低於20")
    if cur["K"] > 80 or cur["D"] > 80:
        signals.append("KD高於80")
    return "、".join(signals) if signals else "無指定訊號"

codes = parse_codes(codes_text)
if not codes:
    st.info("請在左側輸入至少一個股票代號。")
    st.stop()

if st.button("🔄 重新抓取最新資料", type="primary"):
    st.cache_data.clear()

@st.cache_data(ttl=900, show_spinner=False)
def load_one(code, period):
    return get_history(code, period)

rows = []
datasets = {}
failures = []

with st.spinner("正在讀取股票歷史行情並計算 KD…"):
    for code in codes:
        data, ticker, error = load_one(code, period)
        if data is None:
            failures.append((code, error))
            continue
        kd = calculate_kd(data)
        datasets[code] = (kd, ticker)
        last = kd.iloc[-1]
        prev = kd.iloc[-2] if len(kd) > 1 else last
        close = float(last["Close"])
        change_pct = (close / float(prev["Close"]) - 1) * 100 if float(prev["Close"]) else float("nan")
        rows.append({
            "代號": code,
            "名稱": DEFAULT_STOCKS.get(code, ""),
            "資料代號": ticker,
            "資料日期": kd.index[-1].strftime("%Y-%m-%d"),
            "收盤價": round(close, 2),
            "漲跌幅(%)": round(change_pct, 2),
            "K值": round(float(last["K"]), 2),
            "D值": round(float(last["D"]), 2),
            "訊號": get_signal(kd),
        })

if rows:
    result = pd.DataFrame(rows)
    latest_date = max(result["資料日期"])
    st.caption(f"資料更新時間：{dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}（本機時間）｜最新行情日期：{latest_date}")
    a, b, c, d = st.columns(4)
    a.metric("成功取得", f"{len(rows)} 檔")
    b.metric("黃金交叉", int(result["訊號"].str.contains("黃金交叉").sum()))
    c.metric("死亡交叉", int(result["訊號"].str.contains("死亡交叉").sum()))
    d.metric("高／低檔訊號", int(result["訊號"].str.contains("KD低於20|KD高於80", regex=True).sum()))

    st.subheader("庫存 KD 總覽")
    def highlight_signal(val):
        if "黃金交叉" in str(val):
            return "background-color: #d9f2e6; color: #14532d"
        if "死亡交叉" in str(val):
            return "background-color: #fde2e2; color: #991b1b"
        if "KD低於20" in str(val):
            return "background-color: #dbeafe; color: #1e40af"
        if "KD高於80" in str(val):
            return "background-color: #ffedd5; color: #9a3412"
        return ""
    st.dataframe(
        result.style.map(highlight_signal, subset=["訊號"]),
        use_container_width=True,
        hide_index=True,
    )
    csv = result.to_csv(index=False).encode("utf-8-sig")
    st.download_button("下載今日總覽 CSV", data=csv, file_name=f"台股KD總覽_{dt.date.today().isoformat()}.csv", mime="text/csv")

    if show_chart:
        st.subheader("個股 KD 走勢")
        selected = st.selectbox("選擇股票", list(datasets.keys()))
        kd, ticker = datasets[selected]
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=kd.index, y=kd["K"], mode="lines", name="K值"))
        fig.add_trace(go.Scatter(x=kd.index, y=kd["D"], mode="lines", name="D值"))
        fig.add_hline(y=80, line_dash="dash", annotation_text="80 高檔")
        fig.add_hline(y=20, line_dash="dash", annotation_text="20 低檔")
        fig.update_layout(
            title=f"{selected} {DEFAULT_STOCKS.get(selected, '')} — KD(9,3,3)（資料代號：{ticker}）",
            yaxis_title="KD 值", yaxis_range=[0, 100], hovermode="x unified",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            margin=dict(l=20, r=20, t=65, b=20),
        )
        st.plotly_chart(fig, use_container_width=True)
        st.dataframe(
            kd[["High", "Low", "Close", "K", "D"]].tail(20).round(2).rename(
                columns={"High":"最高價","Low":"最低價","Close":"收盤價","K":"K值","D":"D值"}
            ),
            use_container_width=True,
        )
else:
    st.error("所有股票均未能取得資料。請確認網路連線、代號或稍後重試。")

if failures:
    st.subheader("未能取得的代號")
    for code, error in failures:
        st.warning(f"{code}：{error}。可能原因包括代號變更、資料源缺漏或暫時連線失敗。")

with st.expander("計算方式與使用限制"):
    st.markdown("""
    - 指標：KD(9,3,3)，以日線最高價、最低價、收盤價計算 RSV，再以 1/3 平滑計算 K、D。
    - 黃金交叉：前一交易日 K ≤ D，當日 K > D；死亡交叉相反。
    - 高低檔：只要 K 或 D 任一值低於 20，顯示「KD低於20」；任一值高於 80，顯示「KD高於80」。
    - 訊號使用資料源最新提供的日線；若資料源當日尚未更新，顯示日期可能是上一交易日。
    - Yahoo Finance 為非官方、可能調整的第三方資料源；不保證即時性、完整性或服務持續可用。
    - 此工具只供個人研究，不構成投資建議；KD 訊號不保證未來漲跌。
    """)
