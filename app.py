import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime

# Configuración móvil
st.set_page_config(page_title="SPY 0DTE IC", page_icon="🦅", layout="centered")

st.title("🦅 IRON CONDOR 0DTE")

# --- SIDEBAR: GESTIÓN DE CUENTA ---
st.sidebar.header("💰 Cuenta IBKR")
capital_actual = st.sidebar.slider("Saldo (€)", 20000, 50000, 25000, step=500)
riesgo_pct = st.sidebar.slider("Riesgo Máx (%)", 0.5, 2.0, 1.0, step=0.1)

def analizar_ic_completo():
    try:
        # Descarga rápida
        data = yf.download(["^VIX1D", "SPY"], period="1d", interval="15m", progress=False)
        vix1d = data['Close']['^VIX1D'].iloc[-1]
        vix1d_open = data['Open']['^VIX1D'].iloc
        spy = data['Close']['SPY'].iloc[-1]
        
        var_vix1d = (vix1d / vix1d_open - 1) * 100
        
        # 1. SEMÁFORO
        if var_vix1d > 10:
            st.error(f"🔴 RIESGO EXTREMO ({var_vix1d:.2f}%)")
            st.button("⚠️ CERRAR TODO EN IBKR")
        elif var_vix1d > 5:
            st.warning(f"🟡 VIGILANCIA ({var_vix1d:.2f}%)")
        else:
            st.success(f"🟢 MERCADO ESTABLE ({var_vix1d:.2f}%)")

        # 2. CÁLCULO ESTRATEGIA (ANCHO 5 PUNTOS)
        st.write("### 💎 Estructura Iron Condor")
        st.caption("Estrategia neutral: El SPY debe quedar entre las ventas.")
        
        dist = spy * (vix1d / 100) * 0.32 # Coeficiente adaptativo
        s_call = round(spy + dist)
        s_put = round(spy - dist)
        ancho = 5 # Puntos de seguridad estándar
        
        # Diseño visual de las 4 patas
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### 📈 Lado Call")
            st.error(f"**VENDER:** {s_call}")
            st.info(f"**COMPRAR:** {s_call + ancho}")
            
        with col2:
            st.markdown("#### 📉 Lado Put")
            st.success(f"**VENDER:** {s_put}")
            st.info(f"**COMPRAR:** {s_put - ancho}")

        # 3. GESTIÓN DE CONTRATOS
        st.divider()
        riesgo_monetario = capital_actual * (riesgo_pct / 100)
        lotes = max(1, int(riesgo_monetario / 465)) # 465€ aprox = $500 riesgo
        
        st.metric("Nº de Contratos Sugeridos", f"{lotes} Lotes")
        st.write(f"Riesgo total en esta operación: **{round(riesgo_monetario)}€**")
        
    except:
        st.info("⌛ Esperando apertura (15:30h ES) o revisa conexión.")

if st.button('🚀 GENERAR IRON CONDOR AHORA', use_container_width=True):
    analizar_ic_completo()
