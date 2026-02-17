import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime
import pytz

# 1. CONFIGURACIÓN DE PÁGINA
st.set_page_config(page_title="SPY 0DTE Sentinel", page_icon="🛡️", layout="centered")

def get_market_data():
    sent_tickers = {"vix1d": "^VIX1D", "vvix": "^VVIX", "vix": "^VIX", "vix3m": "^VIX3M"}
    vals = {}
    for k, v in sent_tickers.items():
        try:
            data = yf.Ticker(v).history(period="5d")
            vals[k] = data['Close'].iloc[-1] if not data.empty else 0.0
        except:
            vals[k] = 0.0
    
    try:
        spy_ticker = yf.Ticker("SPY")
        spy_hist = spy_ticker.history(period="2d", interval="5m")
        if spy_hist.empty: return vals, 0, 0, 0, 0
        current_price = spy_hist['Close'].iloc[-1]
        last_date = spy_hist.index[-1].date()
        today_data = spy_hist[spy_hist.index.date == last_date].copy()
        today_data['TP'] = (today_data['High'] + today_data['Low'] + today_data['Close']) / 3
        vwap = (today_data['TP'] * today_data['Volume']).sum() / today_data['Volume'].sum()
        dist_vwap = ((current_price - vwap) / vwap) * 100
        contango = ((vals['vix3m'] / vals['vix']) - 1) * 100 if vals.get('vix', 0) > 0 else 0
        return vals, current_price, vwap, dist_vwap, contango
    except:
        return vals, 0, 0, 0, 0

# --- PUNTO 2: FUNCIÓN DE MOSTRAR ESTRATEGIA CON CÁLCULO DE CAPITAL ---
def mostrar_estrategia(nombre, p_buy, p_sell, c_sell, c_buy, riesgo_max):
    st.subheader(f"📊 Estrategia: {nombre}")
    
    # Cada contrato de spread de 5 puntos arriesga $500
    ancho_spread = 5 
    coste_por_contrato = ancho_spread * 100
    contratos = int(riesgo_max // coste_por_contrato)
    if contratos == 0: contratos = 1 

    df_patas = pd.DataFrame({
        "Acción": ["COMPRA (Protección)", "VENTA (Cobro)", "VENTA (Cobro)", "COMPRA (Protección)"],
        "Tipo": ["PUT", "PUT", "CALL", "CALL"],
        "Strike ($)": [p_buy, p_sell, c_sell, c_buy]
    })
    st.table(df_patas)
    
    c1, c2 = st.columns(2)
    c1.info(f"💡 **Rango:** ${p_sell} - ${c_sell}")
    c2.success(f"⚖️ **Sugerencia:** {contratos} Contrato(s) (Riesgo: ${contratos * coste_por_contrato})")

# 2. INTERFAZ STREAMLIT
st.title("🛡️ SPY 0DTE Sentinel")

# --- PUNTO 3 (A): ENTRADA MANUAL DE CAPITAL ---
capital = st.sidebar.number_input("💰 Capital de la Cuenta ($)", min_value=1000, value=25000, step=500)
riesgo_porcentual = st.sidebar.slider("% Riesgo por operación", 0.5, 5.0, 1.0) / 100
riesgo_maximo = capital * riesgo_porcentual

madrid_tz = pytz.timezone('Europe/Madrid')
st.caption(f"Hora España: {datetime.now(madrid_tz).strftime('%H:%M:%S')} | Gestión de Riesgo: ${riesgo_maximo:.0f} máx.")

if st.button('🚀 LANZAR ESCANEO DE MERCADO', use_container_width=True):
    with st.spinner('Analizando datos...'):
        sent, price, vwap, dist, contango = get_market_data()
        
        if price == 0:
            st.error("Error al conectar con Yahoo Finance.")
        else:
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("VIX1D", f"{sent['vix1d']:.2f}")
            col2.metric("VVIX", f"{sent['vvix']:.2f}")
            col3.metric("VWAP Dist", f"{dist:.2f}%")
            col4.metric("Contango", f"{contango:.1f}%")
            st.write(f"### Precio actual SPY: **${price:.2f}**")
            st.divider()

            # --- PUNTO 3 (B): LLAMADA A LA FUNCIÓN CON CAPITAL VARIABLE ---
            if sent['vix1d'] > 35 or sent['vvix'] > 125 or contango < -2:
                st.error("🚨 ESCENARIO D: NO OPERAR")
            elif sent['vix1d'] > 25:
                st.warning("🟠 ESCENARIO C: ALTA VOLATILIDAD")
                # (Aquí puedes añadir tablas para Call/Put spreads si lo deseas)
                st.write("Considerar Spread Direccional 3%")
            elif 18 <= sent['vix1d'] <= 25:
                mostrar_estrategia("IRON CONDOR 2%", round(price*0.98-5), round(price*0.98), round(price*1.02), round(price*1.02+5), riesgo_maximo)
            else:
                mostrar_estrategia("IRON CONDOR 1%", round(price*0.99-5), round(price*0.99), round(price*1.01), round(price*1.01+5), riesgo_maximo)

st.divider()
st.caption("Ajusta el capital en la barra lateral izquierda.")
