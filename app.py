import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime

st.set_page_config(page_title="台股 KD 追蹤", page_icon="📈", layout="wide")

DEFAULT_STOCKS = ["006208", "00900", "00929", "00941", "2884", "2887", "2892", "4118"]
STOCK_NAMES = {
    "006208": "富邦台50",
    "0050": "元大台灣50",
    "0056": "元大高股息",
    "00900": "富邦特選高股息30",
    "00929": "復華台灣科技優息",
    "00941": "中信上游半導體",
    "2330": "台積電",
    "2884": "玉山金",
    "2887": "台新新光金",
    "2892": "第一金",
    "4118": "友訊",
}

if "watchlist" not in st.session_state:
    st.session_state.watchlist = DEFAULT_STOCKS.copy()

st.title("📈 台股每日 KD 追蹤")
st.caption("每日資料由 Yahoo Finance 提供；台股收盤後資料可能延遲更新。此工具僅供技術指標參考，不構成投資建議。")

with st.expander("➕ 新增股票 / ➖ 刪除股票", expanded=True):
    left, right = st.columns([2, 1])
    with left:
        with st.form("add_stock_form", clear_on_submit=True):
            new_code = st.text_input("新增股票代號", placeholder="例如：2330 或 0050").strip()
            submitted = st.form_submit_button("新增到追蹤清單", use_container_width=True)
            if submitted:
                code = new_code.upper().replace(".TW", "").replace(".TWO", "").strip()
                if not code:
                    st.warning("請先輸入股票代號。")
                elif not code.isdigit():
                    st.warning("請輸入數字股票代號，例如 2330、0050。")
                elif code in st.session_state.watchlist:
                    st.info(f"{code} 已經在追蹤清單中。")
                else:
                    st.session_state.watchlist.append(code)
                    st.success(f"已新增 {code}。")
                    st.rerun()
    with right:
        st.write("**目前追蹤清單**")
        if st.session_state.watchlist:
            remove_code = st.selectbox(
                "選擇要刪除的股票",
                options=st.session_state.watchlist,
                format_func=lambda x: f"{x} {STOCK_NAMES.get(x, '')}".strip(),
                key="remove_code",
            )
            if st.button("刪除此股票", use_container_width=True):
                st.session_state.watchlist = [x for x in st.session_state.watchlist if x != remove_code]
                st.success(f"已刪除 {remove_code}。")
                st.rerun()
        else:
            st.info("清單目前是空的，請先新增股票。")

if not st.session_state.watchlist:
    st.warning("請先新增至少一檔股票，才能查看 KD。")
    st.stop()

st.write("**目前追蹤：** " + "、".join(st.session_state.watchlist))
if st.button("🔄 重新抓取最新資料"):
    st.cache_data.clear()
    st.rerun()

@st.cache_data(ttl=900, show_spinner=False)
def fetch_kd(code: str):
    candidates = [f"{code}.TW", f"{code}.TWO"]
    last_error = None
    hist = None
    used_symbol = None
    for ticker in candidates:
        try:
            data = yf.Ticker(ticker).history(period="6mo", interval="1d", auto_adjust=False)
            if data is not None and not data.empty and {"High", "Low", "Close"}.issubset(data.columns):
                hist = data.dropna(subset=["High", "Low", "Close"]).copy()
                used_symbol = ticker
                if len(hist) >= 10:
                    break
        except Exception as exc:
            last_error = str(exc)
    if hist is None or hist.empty:
        raise ValueError(f"查不到 {code} 的日線資料。請確認代號，或稍後再試。")
    low_n = hist["Low"].rolling(window=9, min_periods=9).min()
    high_n = hist["High"].rolling(window=9, min_periods=9).max()
    spread = (high_n - low_n).replace(0, pd.NA)
    rsv = ((hist["Close"] - low_n) / spread * 100).fillna(50)
    k_values, d_values = [], []
    prev_k, prev_d = 50.0, 50.0
    for value in rsv:
        prev_k = (2 / 3) * prev_k + (1 / 3) * float(value)
        prev_d = (2 / 3) * prev_d + (1 / 3) * prev_k
        k_values.append(prev_k)
        d_values.append(prev_d)
    hist["K"] = k_values
    hist["D"] = d_values
    hist["K_prev"] = hist["K"].shift(1)
    hist["D_prev"] = hist["D"].shift(1)
    hist["Cross"] = ""
    golden = (hist["K"] > hist["D"]) & (hist["K_prev"] <= hist["D_prev"])
    death = (hist["K"] < hist["D"]) & (hist["K_prev"] >= hist["D_prev"])
    hist.loc[golden, "Cross"] = "黃金交叉"
    hist.loc[death, "Cross"] = "死亡交叉"
    last = hist.iloc[-1]
    signal = last["Cross"] if last["Cross"] else ("超買區 (>80)" if last["K"] >= 80 and last["D"] >= 80 else "超賣區 (<20)" if last["K"] <= 20 and last["D"] <= 20 else "—")
    return {
        "code": code,
        "name": STOCK_NAMES.get(code, ""),
        "ticker": used_symbol or candidates[0],
        "date": hist.index[-1].strftime("%Y-%m-%d"),
        "close": float(last["Close"]),
        "K": float(last["K"]),
        "D": float(last["D"]),
        "signal": signal,
        "history": hist.tail(60)[["K", "D"]].copy(),
    }

results = []
errors = []
progress = st.progress(0, text="正在取得股票資料…")
for i, code in enumerate(st.session_state.watchlist):
    try:
        results.append(fetch_kd(code))
    except Exception as exc:
        errors.append(f"{code}：{exc}")
    progress.progress((i + 1) / len(st.session_state.watchlist), text=f"正在取得股票資料…（{i+1}/{len(st.session_state.watchlist)}）")
progress.empty()

if results:
    table = pd.DataFrame([{
        "股票代號": r["code"],
        "名稱": r["name"] or "—",
        "資料日期": r["date"],
        "收盤價": round(r["close"], 2),
        "K 值": round(r["K"], 2),
        "D 值": round(r["D"], 2),
        "訊號": r["signal"],
    } for r in results])
    st.subheader("每日 KD 一覽")
    st.dataframe(table, use_container_width=True, hide_index=True)
    st.download_button(
        "下載 CSV 表格",
        data=table.to_csv(index=False).encode("utf-8-sig"),
        file_name=f"tw_stock_kd_{datetime.now().strftime('%Y%m%d')}.csv",
        mime="text/csv",
        use_container_width=True,
    )
    st.subheader("KD 走勢")
    selected = st.selectbox(
        "選擇要查看走勢的股票",
        options=[r["code"] for r in results],
        format_func=lambda x: f"{x} {STOCK_NAMES.get(x, '')}".strip(),
    )
    chosen = next(r for r in results if r["code"] == selected)
    st.caption(f"{chosen['code']} {chosen['name']}｜資料來源代號：{chosen['ticker']}｜最新資料日期：{chosen['date']}")
    st.line_chart(chosen["history"], y=["K", "D"], use_container_width=True)
    st.caption("K、D 值介於 0–100。常見參考：K、D 同在 80 以上為高檔區，同在 20 以下為低檔區；請勿單憑 KD 作投資決策。")

if errors:
    st.subheader("部分股票無法取得資料")
    for message in errors:
        st.warning(message)
    st.caption("若某檔股票代號的市場後綴不正確、Yahoo Finance 暫時沒有資料，或連線受限，就可能出現此提示。")

st.divider()
st.caption("提醒：新增與刪除清單目前儲存在此瀏覽器的 Streamlit 工作階段；重新開啟新工作階段時，可能會回到預設清單。若希望清單永久保存到不同裝置，需要再加入資料庫或其他儲存方式。")
