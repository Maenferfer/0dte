import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime

# Configuración de pantalla móvil
st.set_page_config(page_title="SPY 0DTE PRO", page_icon="🛡️", layout="centered")

st.title("🛡️ SPY 0DTE MAESTRO")

# --- BARRA LATERAL: GESTIÓN DE CAPITAL ---
st.sidebar.header("💰 Configuración de Cuenta")
capital_actual = st.sidebar.slider("Tu Capital en IBKR (€)", 20000, 50000, 25000, step=500)
riesgo_pct = st.sidebar.slider("Riesgo por Operación (%)", 0.5, 3.0, 1.0, step=0.1)

# --- LÓGICA PRINCIPAL ---
def analizar_mercado_movil():
    try:
        # Descarga de datos rápida
        vols = yf.download(["^VIX", "^VIX1D", "^VVIX", "SPY"], period="1d", interval="15m", progress=False)
        
        vix1d_actual = vols['Close']['^VIX1D'].iloc[-1]
        vix1d_open = vols['Open']['^VIX1D'].iloc[0]
        spy_actual = vols['Close']['SPY'].iloc[-1]
        vvix = vols['Close']['^VVIX'].iloc[-1]
        
        var_vix1d = (vix1d_actual / vix1d_open - 1) * 100
        
        # 1. SEMÁFORO DE RIESGO
        if var_vix1d > 10 or vvix > 115:
            st.error(f"🔴 ROJO: RIESGO EXTREMO ({var_vix1d:.2f}%)")
            st.markdown("**ACCIÓN:** CIERRE INMEDIATO. No operar.")
        elif var_vix1d > 5:
            st.warning(f"🟡 AMARILLO: VIGILANCIA ({var_vix1d:.2f}%)")
            st.markdown("**ACCIÓN:** Reducir contratos o alejar strikes.")
        else:
            st.success(f"🟢 VERDE: MERCADO SEGURO ({var_vix1d:.2f}%)")
            st.markdown("**ACCIÓN:** Operativa normal según el plan.")

        # 2. MÉTRICAS CLAVE
        st.divider()
        c1, c2, c3 = st.columns(3)
        c1.metric("SPY", f"{spy_actual:.2f}")
        c2.metric("VIX1D", f"{vix1d_actual:.2f}")
        c3.metric("VVIX", f"{vvix:.1f}")

        # 3. CALCULADORA DE LOTES DINÁMICA
        st.write("### 🧮 Gestión de Lotes")
        riesgo_euros = capital_actual * (riesgo_pct / 100)
        # Asumiendo spread de 5 puntos ($500 de riesgo por contrato)
        contratos_sugeridos = max(1, int(riesgo_euros / 460)) # 460€ aprox son $500
        
        st.write(f"Con un riesgo del **{riesgo_pct}%**, puedes operar:")
        st.info(f"👉 **{contratos_sugeridos} Contratos** (Riesgo: {round(riesgo_euros)}€)")

        # 4. ESTRUCTURA DE STRIKES (16:30h)
        st.write("### 🎯 Strikes Sugeridos")
        coef = 3.2 if vix1d_actual > 20 else 2.8
        dist = spy_actual * (vix1d_actual / 100) * (coef/10)
        
        st.success(f"**SELL PUT:** {round(spy_actual - dist)}")
        st.error(f"**SELL CALL:** {round(spy_actual + dist)}")
        
        st.caption(f"Datos actualizados: {datetime.now().strftime('%H:%M:%S')}")

    except Exception as e:
        st.info("🕒 Esperando datos de mercado... (Apertura 15:30h)")

if st.button('🚀 ANALIZAR AHORA', use_container_width=True):
    analizar_mercado_movil()
