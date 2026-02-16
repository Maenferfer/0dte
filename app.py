import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime
import pytz

# 1. CONFIGURACIÓN ÚNICA (Debe ser el primer comando de Streamlit)
st.set_page_config(page_title="SPY Sentinel 0DTE", page_icon="🛡️", layout="centered")

# Limpieza de caché (opcional, pero mover fuera del flujo principal si da problemas)
# st.cache_data.clear() 

def get_market_data():
    # Tickers de Sentimiento
    sent_tickers = {"vix1d": "^VIX1D", "vvix": "^VVIX", "vix": "^VIX", "vix3m": "^VIX3M"}
    vals = {}
    for k, v in sent_tickers.items():
        try:
            # period="1d" a veces falla si el mercado está cerrado, usamos "5d" para asegurar último cierre
            data = yf.Ticker(v).history(period="5d")
            vals[k] = data['Close'].iloc[-1]
        except:
            vals[k] = 0
    
    # Datos de SPY para VWAP y Precio
    spy_ticker = yf.Ticker("SPY")
    spy_hist = spy_ticker.history(period="2d", interval="5m")
    
    if spy_hist.empty:
        return vals, 0, 0, 0, 0

    current_price = spy_hist['Close'].iloc[-1]
    
    # Cálculo de VWAP Intradía
    spy_hist['TP'] = (spy_hist['High'] + spy_hist['Low'] + spy_hist['Close']) / 3
    vwap = (spy_hist['TP'] * spy_hist['Volume']).sum() / spy_hist['Volume'].sum()
    dist_vwap = ((current_price - vwap) / vwap) * 100
    
    # Cálculo de Contango (VIX3M vs VIX Spot)
    contango = ((vals['vix3m'] / vals['vix']) - 1) * 100 if vals['vix'] > 0 else 0
    
    return vals, current_price, vwap, dist_vwap, contango

# 2. INTERFAZ VISUAL
st.title("🛡️ SPY 0DTE Sentinel")
madrid_tz = pytz.timezone('Europe/Madrid')
st.caption(f"Hora España: {datetime.now(madrid_tz).strftime('%H:%M:%S')} | Cuenta: $25,000")

if st.button('🚀 LANZAR ESCANEO DE MERCADO', use_container_width=True):
    with st.spinner('Analizando el combo perfecto...'):
        sent, price, vwap, dist, contango = get_market_data()
        
        if price == 0:
            st.error("Error al obtener datos de Yahoo Finance. Reintenta en unos segundos.")
        else:
            # Métricas principales
            m1, m2 = st.columns(2)
            m1.metric("VIX1D", f"{sent['vix1d']:.2f}")
            m2.metric("VVIX", f"{sent['vvix']:.2f}")
            
            m3, m4 = st.columns(2)
            m3.metric("Dist. VWAP", f"{dist:.2f}%")
            m4.metric("Contango", f"{contango:.1f}%")

            st.divider()

            # 3. LÓGICA DE DECISIÓN
            if sent['vix1d'] > 35 or sent['vvix'] > 125 or contango < -2:
                st.error("🚨 ESCENARIO D: NO OPERAR")
                st.warning("Riesgo de Cisne Negro detectado. Protege tus $25k.")
            
            elif sent['vix1d'] > 25:
                st.warning("🟠 ESCENARIO C: ALTA VOLATILIDAD (3%)")
                if dist < -0.60:
                    s_call, l_call = round(price * 1.03), round(price * 1.03 + 20)
                    st.success(f"**BEAR CALL SPREAD**\n\nVende Call: {s_call} / Compra Call: {l_call}")
                else:
                    s_put, l_put = round(price * 0.97), round(price * 0.97 - 20)
                    st.success(f"**BULL PUT SPREAD**\n\nVende Put: {s_put} / Compra Put: {l_put}")
                
            elif 18 <= sent['vix1d'] <= 25:
                st.info("🟡 ESCENARIO B: VOL. MODERADA (2%)")
                if abs(dist) > 0.40:
                    if dist > 0:
                        s_put, l_put = round(price * 0.98), round(price * 0.98 - 10)
                        st.success(f"**BULL PUT SPREAD**\n\nVende Put: {s_put} / Compra Put: {l_put}")
                    else:
                        s_call, l_call = round(price * 1.02), round(price * 1.02 + 10)
                        st.success(f"**BEAR CALL SPREAD**\n\nVende Call: {s_call} / Compra Call: {l_call}")
                else:
                    sp, lp = round(price * 0.98), round(price * 0.98 - 10)
                    sc, lc = round(price * 1.02), round(price * 1.02 + 10)
                    st.success(f"**IRON CONDOR 2%**\n\nPut: {lp}/{sp} -- Call: {sc}/{lc}")

            else:
                st.success("🟢 ESCENARIO A: CALMA TOTAL (1%)")
                sp, lp = round(price * 0.99), round(price * 0.99 - 10)
                sc, lc = round(price * 1.01), round(price * 1.01 + 10)
                st.write(f"**IRON CONDOR**\n\nPut: {lp}/{sp} -- Call: {sc}/{lc}")

st.divider()
st.caption("Estrategia basada en el estudio estadístico del VIX1D (2023-2026).")
