import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime
import pytz

# ─────────────────────────────────────────
# 1. CONFIGURACIÓN DE PÁGINA
# ─────────────────────────────────────────
st.set_page_config(page_title="SPY 0DTE Sentinel", page_icon="🛡️", layout="centered")

# ─────────────────────────────────────────
# 2. SESSION STATE (historial de señales)
# ─────────────────────────────────────────
if "historial" not in st.session_state:
    st.session_state.historial = []
if "ultimo_scan" not in st.session_state:
    st.session_state.ultimo_scan = None

# ─────────────────────────────────────────
# 3. HELPERS DE TIEMPO
# ─────────────────────────────────────────
ET = pytz.timezone("America/New_York")
MADRID = pytz.timezone("Europe/Madrid")

def hora_et_actual():
    return datetime.now(ET)

def mercado_abierto():
    """True si estamos en horario útil para 0DTE: 10:00-15:30 ET en día laborable."""
    now = hora_et_actual()
    if now.weekday() >= 5:          # sábado / domingo
        return False, "Mercado cerrado (fin de semana)"
    t = now.time()
    from datetime import time
    if t < time(10, 0):
        return False, f"Demasiado temprano — abre para operar a las 10:00 ET ({now.strftime('%H:%M')} ET ahora)"
    if t > time(15, 30):
        return False, f"Demasiado tarde — ventana 0DTE cerrada a las 15:30 ET ({now.strftime('%H:%M')} ET ahora)"
    return True, f"✅ Ventana operativa ({now.strftime('%H:%M')} ET)"

# ─────────────────────────────────────────
# 4. CARGA DE DATOS
# ─────────────────────────────────────────
def calcular_rsi(series, periodo=14):
    delta = series.diff()
    ganancia = delta.clip(lower=0).rolling(periodo).mean()
    perdida = (-delta.clip(upper=0)).rolling(periodo).mean()
    rs = ganancia / perdida.replace(0, np.nan)
    return 100 - (100 / (1 + rs))

def get_market_data():
    sent_tickers = {"vix1d": "^VIX1D", "vvix": "^VVIX", "vix": "^VIX", "vix3m": "^VIX3M"}
    vals = {}

    for k, v in sent_tickers.items():
        try:
            ticker = yf.Ticker(v)
            data = ticker.history(period="5d")
            vals[k] = float(data["Close"].iloc[-1]) if not data.empty else 0.0
        except:
            vals[k] = 0.0

    # Fallback VIX1D
    if vals.get("vix1d", 0) == 0 or pd.isna(vals.get("vix1d")):
        vals["vix1d"] = vals.get("vix", 20.0)
        st.sidebar.warning("⚠️ VIX1D no disponible — usando VIX estándar.")

    try:
        spy = yf.Ticker("SPY")
        hist = spy.history(period="2d", interval="5m")
        if hist.empty:
            return vals, 0, 0, 0, 0, 0, 0, 0

        precio = float(hist["Close"].iloc[-1])
        last_date = hist.index[-1].date()
        hoy = hist[hist.index.date == last_date].copy()

        # VWAP
        hoy["TP"] = (hoy["High"] + hoy["Low"] + hoy["Close"]) / 3
        vwap = (hoy["TP"] * hoy["Volume"]).sum() / hoy["Volume"].sum()
        dist_vwap = ((precio - vwap) / vwap) * 100

        # Contango
        contango = ((vals["vix3m"] / vals["vix"]) - 1) * 100 if vals.get("vix", 0) > 0 else 0

        # RSI (14 periodos de 5min ≈ ~70 min)
        rsi = calcular_rsi(hoy["Close"], 14).iloc[-1] if len(hoy) >= 14 else 50.0

        # Media 9 velas
        ma9 = hoy["Close"].rolling(9).mean().iloc[-1] if len(hoy) >= 9 else precio
        sobre_ma9 = precio > ma9

        # Movimiento esperado diario con VIX1D
        mov_esperado = (vals["vix1d"] / 100) / np.sqrt(252) * precio

        return vals, precio, vwap, dist_vwap, contango, rsi, sobre_ma9, mov_esperado

    except:
        return vals, 0, 0, 0, 0, 50, True, 0

# ─────────────────────────────────────────
# 5. MOSTRAR ESTRATEGIA (strikes dinámicos)
# ─────────────────────────────────────────
def mostrar_estrategia(nombre, precio, mov_esperado, multiplicador, riesgo_max):
    st.subheader(f"📊 Estrategia: {nombre}")

    margen = mov_esperado * multiplicador
    p_sell = round(precio - margen)
    p_buy  = p_sell - 5
    c_sell = round(precio + margen)
    c_buy  = c_sell + 5

    st.info(
        f"📐 Movimiento esperado hoy: **±${mov_esperado:.1f}** "
        f"(VIX1D → fórmula estándar de mercado)"
    )

    df_patas = pd.DataFrame({
        "Acción": ["COMPRA (Protección)", "VENTA (Cobro)", "VENTA (Cobro)", "COMPRA (Protección)"],
        "Tipo":   ["PUT", "PUT", "CALL", "CALL"],
        "Strike ($)": [p_buy, p_sell, c_sell, c_buy],
    })
    st.table(df_patas)

    ancho_spread = 5
    coste_por_contrato = ancho_spread * 100
    contratos = max(1, int(riesgo_max // coste_por_contrato))

    c1, c2 = st.columns(2)
    c1.info(f"💡 **Rango:** ${p_sell} – ${c_sell}")
    c2.success(f"⚖️ **Sugerencia:** {contratos} contrato(s)  |  Riesgo: ${contratos * coste_por_contrato}")

    return nombre, p_sell, c_sell

# ─────────────────────────────────────────
# 6. SEMÁFORO VISUAL
# ─────────────────────────────────────────
def mostrar_semaforo(escenario, razones):
    colores = {
        "D": ("#ff4444", "🔴", "NO OPERAR"),
        "C": ("#ff9900", "🟠", "ALTA VOLATILIDAD"),
        "B": ("#00cc88", "🟢", "IRON CONDOR 2%"),
        "A": ("#00ff99", "🟢", "IRON CONDOR 1%"),
    }
    color, emoji, label = colores[escenario]
    st.markdown(
        f"""
        <div style="
            background:{color}22;
            border:2px solid {color};
            border-radius:12px;
            padding:16px 20px;
            margin-bottom:12px;
        ">
            <div style="font-size:2rem;font-weight:900;color:{color}">
                {emoji} ESCENARIO {escenario}: {label}
            </div>
            <ul style="margin-top:8px;color:#ddd;font-size:0.95rem">
                {"".join(f"<li>{r}</li>" for r in razones)}
            </ul>
        </div>
        """,
        unsafe_allow_html=True,
    )

# ─────────────────────────────────────────
# 7. INTERFAZ PRINCIPAL
# ─────────────────────────────────────────
st.title("🛡️ SPY 0DTE Sentinel")

# Sidebar
capital           = st.sidebar.number_input("💰 Capital ($)", min_value=1000, value=25000, step=500)
riesgo_porcentual = st.sidebar.slider("% Riesgo por operación", 0.5, 5.0, 1.0) / 100
riesgo_maximo     = capital * riesgo_porcentual

auto_refresh      = st.sidebar.toggle("🔄 Auto-refresco (5 min)", value=False)
mostrar_historial = st.sidebar.toggle("📋 Mostrar historial", value=True)

now_madrid = datetime.now(MADRID).strftime("%H:%M:%S")
operable, msg_hora = mercado_abierto()

st.caption(f"Hora España: {now_madrid}  |  Gestión de Riesgo: ${riesgo_maximo:.0f} máx.")

# Aviso de horario
if not operable:
    st.warning(f"⏰ {msg_hora}")
else:
    st.success(msg_hora)

# ─── Botón de escaneo ───
disparar = st.button("🚀 LANZAR ESCANEO DE MERCADO", use_container_width=True)

# Auto-refresco: rerun automático si está activado y el mercado está abierto
if auto_refresh and operable:
    import time
    ultimo = st.session_state.ultimo_scan
    ahora  = datetime.now().timestamp()
    if ultimo is None or (ahora - ultimo) >= 300:   # 5 minutos
        disparar = True

if disparar:
    with st.spinner("Analizando datos del mercado..."):
        sent, precio, vwap, dist, contango, rsi, sobre_ma9, mov_esp = get_market_data()
        st.session_state.ultimo_scan = datetime.now().timestamp()

    if precio == 0:
        st.error("❌ Error al conectar con Yahoo Finance. Inténtalo de nuevo.")
    else:
        # ── Métricas ──
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("VIX1D",      f"{sent['vix1d']:.2f}")
        col2.metric("VVIX",       f"{sent['vvix']:.2f}")
        col3.metric("VWAP Dist",  f"{dist:.2f}%")
        col4.metric("Contango",   f"{contango:.1f}%")

        col5, col6, col7 = st.columns(3)
        col5.metric("RSI 5min",   f"{rsi:.1f}")
        col6.metric("vs MA9",     "↑ Por encima" if sobre_ma9 else "↓ Por debajo")
        col7.metric("Mov. esperado", f"±${mov_esp:.1f}")

        st.write(f"### Precio actual SPY: **${precio:.2f}**")
        st.divider()

        # ── Lógica de escenarios ──
        razones_d, razones_c = [], []
        if sent["vix1d"] > 35:   razones_d.append(f"VIX1D={sent['vix1d']:.1f} > 35")
        if sent["vvix"] > 125:   razones_d.append(f"VVIX={sent['vvix']:.1f} > 125")
        if contango < -2:        razones_d.append(f"Contango={contango:.1f}% (backwardation severa)")
        if not operable:         razones_d.append(f"Fuera de ventana horaria — {msg_hora}")

        if sent["vix1d"] > 25:   razones_c.append(f"VIX1D={sent['vix1d']:.1f} > 25")

        if razones_d:
            mostrar_semaforo("D", razones_d)
            estrategia_nombre = "NO OPERAR"
            p_sell = c_sell = "-"

        elif razones_c:
            mostrar_semaforo("C", razones_c + ["Considerar Spread Direccional 3%"])
            st.write("Considerar Spread Direccional al 3% del precio actual.")
            estrategia_nombre = "ESCENARIO C"
            p_sell = c_sell = "-"

        elif 18 <= sent["vix1d"] <= 25:
            mostrar_semaforo("B", [
                f"VIX1D={sent['vix1d']:.1f} en zona media (18-25)",
                "Iron Condor con margen 1× movimiento esperado",
            ])
            estrategia_nombre, p_sell, c_sell = mostrar_estrategia(
                "IRON CONDOR 2%", precio, mov_esp, 1.0, riesgo_maximo
            )
        else:
            mostrar_semaforo("A", [
                f"VIX1D={sent['vix1d']:.1f} < 18 (baja volatilidad)",
                "Iron Condor con margen 0.7× movimiento esperado",
            ])
            estrategia_nombre, p_sell, c_sell = mostrar_estrategia(
                "IRON CONDOR 1%", precio, mov_esp, 0.7, riesgo_maximo
            )

        # ── Guardar en historial ──
        ts = datetime.now(MADRID).strftime("%H:%M:%S")
        st.session_state.historial.append({
            "Hora (ES)": ts,
            "SPY":       f"${precio:.2f}",
            "VIX1D":     f"{sent['vix1d']:.1f}",
            "VVIX":      f"{sent['vvix']:.1f}",
            "Escenario": estrategia_nombre,
            "Put sell":  p_sell,
            "Call sell": c_sell,
        })

# ─── Historial del día ───
if mostrar_historial and st.session_state.historial:
    st.divider()
    st.subheader("📋 Historial de señales de hoy")
    df_hist = pd.DataFrame(st.session_state.historial[::-1])   # más reciente arriba
    st.dataframe(df_hist, use_container_width=True, hide_index=True)
    if st.button("🗑️ Limpiar historial"):
        st.session_state.historial = []
        st.rerun()

# ── Auto-refresco: programar próximo ciclo ──
if auto_refresh and operable:
    import time
    tiempo_restante = max(0, 300 - int(datetime.now().timestamp() - (st.session_state.ultimo_scan or 0)))
    st.caption(f"⏱️ Próximo refresco automático en {tiempo_restante}s")
    time.sleep(min(tiempo_restante, 30))
    st.rerun()

st.divider()
st.caption("Ajusta el capital y opciones en la barra lateral izquierda.")
