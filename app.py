import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime
import pytz

# 1. CONFIGURACIÓN ÚNICA
st.set_page_config(page_title="SPY Sentinel 0DTE", page_icon="🛡️", layout="centered")

def get_market_data():
    # Tickers de Sentimiento
    sent_tickers = {"vix1d": "^VIX1D", "vvix": "^VVIX", "vix": "^VIX", "vix3m": "^VIX3M"}
    vals = {}
    
    for k, v in sent_tickers.items():
        try:
            # Usamos period 5d para asegurar que siempre haya un dato de cierre disponible
            ticker = yf.Ticker(v)
            data = ticker.history(period="5d")
            if not data.empty:
                vals[k] = data['Close'].iloc[-1]
            else:
                vals[k] = 0.0
        except Exception:
            vals[k] = 0.0
    
    # Datos de SPY para VWAP y Precio
    try:
        spy_ticker = yf.Ticker("SPY")
        # Es vital usar 2d y 5m para el VWAP intradía
        spy_hist = spy_ticker.history(period="2d", interval="5m")
        
        if spy_hist.empty or len(spy_hist) < 2:
            return vals, 0, 0, 0, 0

        current_price = spy_hist['Close'].iloc[-1]
        
        # Cálculo de VWAP del día actual
        # Filtramos solo los datos de la última sesión disponible
        last_date = spy_hist.index[-1].date()
        day_data = spy_hist[spy_hist.index.date == last_date].copy()
        
        day_data['TP'] = (day_data['High'] + day_data['Low'] + day_data['Close']) / 3
        vwap = (day_data['TP'] * day_data['Volume']).sum() / day_data['Volume'].sum()
        dist_vwap = ((current_price - vwap) / vwap) * 100
        
        # Cálculo de Contango (VIX3M vs VIX Spot)
        contango = ((vals['vix3m'] / vals['vix']) - 1) * 100 if vals.get('vix', 0) > 0 else 0
        
        return vals, current_price, vwap, dist_vwap, contango
    except Exception as e:
        st.error(f"Error técnico: {e}")
        return vals, 0, 0, 0, 0

# 2. INTERFAZ VISUAL
st.title("🛡️ SPY 0DTE Sentinel")
madrid_tz = pytz.timezone('Europe/Madrid')
st.caption(f"Hora España: {datetime.now(madrid_tz).strftime('%H:%M:%S')} | Cuenta: $25,000")

if st.button('🚀 LANZAR ESCANEO DE MERCADO', use_container_width=True):
    with st.spinner('Extrayendo datos de Yahoo Finance...'):
        sent, price, vwap, dist, contango = get_market_data()
        
        if price == 0 or sent['vix'] == 0:
            st.error("No se pudieron obtener datos. El mercado podría estar cerrado o Yahoo Finance no responde.")
        else:
            # Mostrar métricas
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("VIX1D", f"{sent['vix1d']:.2f}")
            col2.metric("VVIX", f"{sent['vvix']:.2f}")
            col3.metric("VWAP Dist", f"{dist:.2f}%")
            col4.metric("Contango", f"{contango:.1f}%")

            st.subheader(f"Precio Actual SPY: ${price:.2f}")
            st.divider()

            # 3. LÓGICA DE DECISIÓN
            if sent['vix1d'] > 35 or sent['vvix'] > 125 or contango < -2:
                st.error("🚨 ESCENARIO D: NO OPERAR - Riesgo Extremo")
            
            elif sent['vix1d'] > 25:
                st.warning("🟠 ESCENARIO C: ALTA VOLATILIDAD (3%)")
                if dist < -0.60:
                    st.success(f"**BEAR CALL SPREAD**\n\nVende Call: {round(price * 1.03)} / Compra Call: {round(price * 1.03 + 5)}")
                else:
                    st.success(f"**BULL PUT SPREAD**\n\nVende Put: {round(price * 0.97)} / Compra Put: {round(price * 0.97 - 5)}")
                
            elif 18 <= sent['vix1d'] <= 25:
                st.info("🟡 ESCENARIO B: VOL. MODERADA (2%)")
                if abs(dist) > 0.40:
                    if dist > 0:
                        st.success(f"**BULL PUT SPREAD**\n\nVende Put: {round(price * 0.98)} / Compra Put: {round(price * 0.98 - 5)}")
                    else:
                        st.success(f"**BEAR CALL SPREAD**\n\nVende Call: {round(price * 1.02)} / Compra Call: {round(price * 1.02 + 5)}")
                else:
                    st.success(f"**IRON CONDOR 2%**\n\nPut: {round(price*0.98-5)}/{round(price*0.98)} -- Call: {round(price*1.02)}/{round(price*1.02+5)}")

            else:
                st.success("🟢 ESCENARIO A: CALMA TOTAL (1%)")
                st.write(f"**IRON CONDOR 1%**\n\nPut: {round(price*0.99-5)}/{round(price*0.99)} -- Call: {round(price*1.01)}/{round(price*1.01+5)}")

st.divider()
st.caption("Nota: Los niveles de spread se han ajustado a 5 puntos de ancho para mejor liquidez.")
