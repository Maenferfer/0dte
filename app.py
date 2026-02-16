import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime
import pytz

# 1. CONFIGURACIÓN DE PÁGINA
st.set_page_config(page_title="SPY 0DTE Sentinel", page_icon="🛡️", layout="centered")

def get_market_data():
    # Tickers de Sentimiento
    sent_tickers = {"vix1d": "^VIX1D", "vvix": "^VVIX", "vix": "^VIX", "vix3m": "^VIX3M"}
    vals = {}
    
    for k, v in sent_tickers.items():
        try:
            ticker = yf.Ticker(v)
            data = ticker.history(period="5d")
            vals[k] = data['Close'].iloc[-1] if not data.empty else 0.0
        except:
            vals[k] = 0.0
    
    # Datos de SPY para VWAP y Precio
    try:
        spy_ticker = yf.Ticker("SPY")
        spy_hist = spy_ticker.history(period="2d", interval="5m")
        
        if spy_hist.empty:
            return vals, 0, 0, 0, 0

        current_price = spy_hist['Close'].iloc[-1]
        
        # Filtrar solo datos de hoy para el VWAP
        last_date = spy_hist.index[-1].date()
        today_data = spy_hist[spy_hist.index.date == last_date].copy()
        
        today_data['TP'] = (today_data['High'] + today_data['Low'] + today_data['Close']) / 3
        vwap = (today_data['TP'] * today_data['Volume']).sum() / today_data['Volume'].sum()
        dist_vwap = ((current_price - vwap) / vwap) * 100
        
        contango = ((vals['vix3m'] / vals['vix']) - 1) * 100 if vals.get('vix', 0) > 0 else 0
        
        return vals, current_price, vwap, dist_vwap, contango
    except:
        return vals, 0, 0, 0, 0

def mostrar_estrategia(nombre, p_buy, p_sell, c_sell, c_buy):
    st.subheader(f"📊 Estrategia: {nombre}")
    df_patas = pd.DataFrame({
        "Acción": ["COMPRA (Protección)", "VENTA (Cobro)", "VENTA (Cobro)", "COMPRA (Protección)"],
        "Tipo": ["PUT", "PUT", "CALL", "CALL"],
        "Strike ($)": [p_buy, p_sell, c_sell, c_buy]
    })
    st.table(df_patas)
    st.info(f"💡 **Rango de Ganancia:** El SPY debe quedar entre ${p_sell} y ${c_sell} al cierre.")

# 2. INTERFAZ STREAMLIT
st.title("🛡️ SPY 0DTE Sentinel")
madrid_tz = pytz.timezone('Europe/Madrid')
st.caption(f"Hora España: {datetime.now(madrid_tz).strftime('%H:%M:%S')} | Capital: $25,000")

if st.button('🚀 LANZAR ESCANEO DE MERCADO', use_container_width=True):
    with st.spinner('Analizando volatilidad y strikes...'):
        sent, price, vwap, dist, contango = get_market_data()
        
        if price == 0:
            st.error("Error al conectar con Yahoo Finance. Reintenta.")
        else:
            # Métricas
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("VIX1D", f"{sent['vix1d']:.2f}")
            col2.metric("VVIX", f"{sent['vvix']:.2f}")
            col3.metric("VWAP Dist", f"{dist:.2f}%")
            col4.metric("Contango", f"{contango:.1f}%")

            st.write(f"### Precio actual SPY: **${price:.2f}**")
            st.divider()

            # 3. LÓGICA DE DECISIÓN (LAS 4 PATAS)
            # ESCENARIO D: RIESGO EXTREMO
            if sent['vix1d'] > 35 or sent['vvix'] > 125 or contango < -2:
                st.error("🚨 ESCENARIO D: NO OPERAR")
                st.warning("Condiciones de mercado peligrosas. Protege tu capital.")

            # ESCENARIO C: ALTA VOLATILIDAD (Spreads Direccionales)
            elif sent['vix1d'] > 25:
                st.warning("🟠 ESCENARIO C: ALTA VOLATILIDAD (3% de margen)")
                if dist < -0.60:
                    st.write("**Bear Call Spread (Bajista)**")
                    s_c, b_c = round(price * 1.03), round(price * 1.03 + 5)
                    st.latex(f"Sell~Call~{s_c}~/~Buy~Call~{b_c}")
                else:
                    st.write("**Bull Put Spread (Alcista)**")
                    s_p, b_p = round(price * 0.97), round(price * 0.97 - 5)
                    st.latex(f"Sell~Put~{s_p}~/~Buy~Put~{b_p}")

            # ESCENARIO B: VOLATILIDAD MODERADA (Iron Condor 2%)
            elif 18 <= sent['vix1d'] <= 25:
                if abs(dist) > 0.40:
                    st.info("🟡 ESCENARIO B: DIRECCIONAL (2%)")
                    if dist > 0:
                        s_p, b_p = round(price * 0.98), round(price * 0.98 - 5)
                        st.write(f"**BULL PUT:** Vende {s_p}P / Compra {b_p}P")
                    else:
                        s_c, b_c = round(price * 1.02), round(price * 1.02 + 5)
                        st.write(f"**BEAR CALL:** Vende {s_c}C / Compra {b_c}C")
                else:
                    mostrar_estrategia(
                        "IRON CONDOR 2% (Vol. Moderada)",
                        round(price * 0.98 - 5), # Buy Put
                        round(price * 0.98),     # Sell Put
                        round(price * 1.02),     # Sell Call
                        round(price * 1.02 + 5)  # Buy Call
                    )

            # ESCENARIO A: CALMA (Iron Condor 1%)
            else:
                mostrar_estrategia(
                    "IRON CONDOR 1% (Calma Total)",
                    round(price * 0.99 - 5), # Buy Put
                    round(price * 0.99),     # Sell Put
                    round(price * 1.01),     # Sell Call
                    round(price * 1.01 + 5)  # Buy Call
                )

st.divider()
st.caption("Configuración: Ancho de alas (Spread) de $5. Ajuste basado en desviación estándar VIX1D.")
