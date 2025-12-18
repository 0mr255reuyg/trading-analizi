import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import pandas_ta as ta
import plotly.graph_objects as go
from datetime import datetime, timedelta

# ======================================================
# PAGE CONFIG
# ======================================================
st.set_page_config(
    page_title="BIST Pro Analiz",
    page_icon="📊",
    layout="wide"
)

# ======================================================
# CSS – DARK THEME
# ======================================================
st.markdown("""
<style>
body { background-color: #0e1117; }
.box {
    background: #111827;
    padding: 16px;
    border-radius: 12px;
    box-shadow: 0 0 10px rgba(0,0,0,.4);
}
.score {
    font-size: 34px;
    font-weight: bold;
    color: #22c55e;
}
.al { color: #22c55e; font-weight: bold; }
.bekle { color: #eab308; font-weight: bold; }
.sat { color: #ef4444; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

# ======================================================
# BIST LIST
# ======================================================
BIST = {
    "ASELSAN": "ASELS.IS",
    "THYAO": "THYAO.IS",
    "KCHOL": "KCHOL.IS",
    "TUPRS": "TUPRS.IS",
    "BIMAS": "BIMAS.IS",
    "AKBNK": "AKBNK.IS",
    "GARAN": "GARAN.IS",
    "EREGL": "EREGL.IS",
    "SASA": "SASA.IS",
    "SISE": "SISE.IS"
}

# ======================================================
# DATA
# ======================================================
@st.cache_data(ttl=900)
def load_data(symbol):
    df = yf.download(
        symbol,
        period="1y",
        interval="1d",
        progress=False
    )
    df.dropna(inplace=True)
    return df

# ======================================================
# INDICATORS
# ======================================================
def indicators(df):
    df["RSI"] = ta.rsi(df.Close, 14)
    macd = ta.macd(df.Close)
    df["MACD"] = macd.iloc[:, 0]
    df["SIGNAL"] = macd.iloc[:, 1]
    df["MFI"] = ta.mfi(df.High, df.Low, df.Close, df.Volume)
    adx = ta.adx(df.High, df.Low, df.Close)
    df["ADX"] = adx.iloc[:, 0]
    df["DI+"] = adx.iloc[:, 1]
    df["DI-"] = adx.iloc[:, 2]
    stt = ta.supertrend(df.High, df.Low, df.Close, 10, 3)
    df["ST"] = stt.iloc[:, 0]
    bb = ta.bbands(df.Close)
    df["BBP"] = bb.iloc[:, 4]
    df["ATR"] = ta.atr(df.High, df.Low, df.Close)
    df["SMA20"] = ta.sma(df.Close, 20)
    df["SMA50"] = ta.sma(df.Close, 50)
    return df

# ======================================================
# SCORING
# ======================================================
def score_calc(df):
    s = 0
    l, p = df.iloc[-1], df.iloc[-2]

    if 55 <= l.RSI <= 60: s += 20
    elif 50 <= l.RSI < 55 or 60 < l.RSI <= 65: s += 15
    elif 45 <= l.RSI < 50 or 65 < l.RSI <= 70: s += 10

    if l.MACD > l.SIGNAL:
        if l.MACD > 0 and l.MACD > p.MACD: s += 20
        elif l.MACD > 0: s += 15
        else: s += 12

    vol_avg = df.Volume.rolling(20).mean().iloc[-1]
    if l.Volume > vol_avg * 1.5 and 50 <= l.MFI <= 80: s += 20
    elif l.Volume > vol_avg * 1.2 and l.MFI > p.MFI: s += 15
    elif l.Volume > vol_avg: s += 10

    if l.ADX > 25 and l["DI+"] > l["DI-"]: s += 15
    elif 20 <= l.ADX <= 25 and l.ADX > p.ADX: s += 10

    if l.Close > l.ST: s += 15
    if l.BBP > 0.8: s += 10
    elif 0.5 < l.BBP <= 0.8: s += 5

    return min(s, 100)

# ======================================================
# RECOMMENDATION
# ======================================================
def recommendation(score):
    if score >= 75:
        return "AL", "al"
    elif score >= 55:
        return "TAKİP", "bekle"
    else:
        return "BEKLE", "sat"

# ======================================================
# BACKTEST
# ======================================================
def backtest(df, threshold=70):
    capital = 100000
    position = 0
    entry = 0

    for i in range(50, len(df)):
        sub = df.iloc[:i]
        sc = score_calc(sub)
        price = sub.Close.iloc[-1]

        if sc >= threshold and position == 0:
            position = capital / price
            entry = price
            capital = 0

        elif sc < threshold and position > 0:
            capital = position * price
            position = 0

    total = capital if capital > 0 else position * df.Close.iloc[-1]
    return total

# ======================================================
# SIDEBAR
# ======================================================
st.sidebar.title("📊 BIST PRO ANALİZ")
stock = st.sidebar.selectbox("Hisse", list(BIST.keys()))
compare = st.sidebar.multiselect("Karşılaştır", list(BIST.keys()))
alarm_score = st.sidebar.slider("Alarm Skor Seviyesi", 50, 100, 75)
run = st.sidebar.button("🚀 Analizi Başlat")

# ======================================================
# MAIN
# ======================================================
if run:
    try:
        df = indicators(load_data(BIST[stock]))
        sc = score_calc(df)
        rec, cls = recommendation(sc)
        last = df.iloc[-1]

        sl = last.Close - 2 * last.ATR
        tp = last.Close + 3 * last.ATR

        fig = go.Figure()
        fig.add_candlestick(
            x=df.index,
            open=df.Open,
            high=df.High,
            low=df.Low,
            close=df.Close
        )
        fig.add_scatter(x=df.index, y=df.SMA20, name="SMA20")
        fig.add_scatter(x=df.index, y=df.SMA50, name="SMA50")
        fig.update_layout(template="plotly_dark", height=600)
        st.plotly_chart(fig, use_container_width=True)

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Fiyat", f"{last.Close:.2f} ₺")
        c2.metric("Skor", f"{sc}/100")
        c3.metric("Stop", f"{sl:.2f}")
        c4.metric("Hedef", f"{tp:.2f}")

        st.markdown(f"### 🔔 Öneri: <span class='{cls}'>{rec}</span>", unsafe_allow_html=True)

        if sc >= alarm_score:
            st.warning("🚨 ALARM: Skor hedef seviyeye ulaştı!")

        # =========================
        # COMPARISON
        # =========================
        if compare:
            rows = []
            for s in compare:
                d = indicators(load_data(BIST[s]))
                rows.append({
                    "Hisse": s,
                    "Skor": score_calc(d),
                    "Fiyat": d.Close.iloc[-1]
                })
            st.subheader("📌 Çoklu Hisse Karşılaştırma")
            st.dataframe(pd.DataFrame(rows).sort_values("Skor", ascending=False))

        # =========================
        # BACKTEST
        # =========================
        st.subheader("📈 Backtest Sonucu")
        final_cap = backtest(df)
        st.info(f"Başlangıç: 100.000 ₺ → Sonuç: {final_cap:,.0f} ₺")

    except Exception as e:
        st.error("❌ Veri alınamadı veya hesaplama hatası oluştu.")
