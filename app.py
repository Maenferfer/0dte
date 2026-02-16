import yfinance as yf
import pandas as pd
from datetime import datetime

def get_market_sentiment():
    """Obtiene VIX, VIX3M, VIX1D y VVIX de forma robusta"""
    tickers = {
        "vix1d": "^VIX1D",
        "vvix": "^VVIX",
        "vix_spot": "^VIX",
        "vix3m": "^VIX3M"
    }
    data = {}
    for key, symbol in tickers.items():
        try:
            val = yf.Ticker(symbol).history(period="1d")['Close'].iloc[-1]
            data[key] = val
        except:
            data[key] = 0
    
    # Cálculo de Contango alternativo (VIX3M / VIX) si los futuros fallan
    # Un ratio > 1 indica Contango (viento a favor)
    try:
        contango_ratio = (data['vix3m'] / data['vix_spot']) if data['vix_spot'] > 0 else 0
        contango_pct = (contango_ratio - 1) * 100
    except:
        contango_pct = 0
        
    return data, contango_pct

def analyze_master_strategy():
    print(f"\n{'='*60}")
    print(f" SENTINEL SPY 0DTE - ESTRATEGIA MAESTRA (Hora ES: {datetime.now().strftime('%H:%M:%S')})")
    print(f"{'='*60}\n")
    
    # 1. CAPTURA DE DATOS
    spy = yf.Ticker("SPY")
    sent, contango_pct = get_market_sentiment()
    
    spy_hist = spy.history(period="2d", interval="5m")
    if spy_hist.empty:
        print("Error: No se han podido descargar datos del SPY.")
        return

    current_price = spy_hist['Close'].iloc[-1]
    
    # 2. CÁLCULO DE VWAP
    spy_hist['TP'] = (spy_hist['High'] + spy_hist['Low'] + spy_hist['Close']) / 3
    vwap = (spy_hist['TP'] * spy_hist['Volume']).sum() / spy_hist['Volume'].sum()
    dist_vwap = ((current_price - vwap) / vwap) * 100

    # 3. IMPRESIÓN DE FILTROS
    print(f"--- FILTROS DE MERCADO ---")
    print(f"VIX1D: {sent['vix1d']:.2f} | VVIX: {sent['vvix']:.2f}")
    print(f"Estructura Vol: {'CONTANGO' if contango_pct > 0 else 'BACKWARDATION'} ({contango_pct:.2f}%)")
    print(f"Dist. VWAP: {dist_vwap:.2f}% | SPY: ${current_price:.2f}")
    print("-" * 60)

    # 4. LÓGICA DE DECISIÓN
    if sent['vix1d'] > 35 or sent['vvix'] > 125 or contango_pct < -2:
        print("🚨 ESCENARIO D: RIESGO EXTREMO")
        print(">>> DECISIÓN: NO OPERAR. PROTEGE TUS $25.000.")

    elif sent['vix1d'] > 25:
        dist = 0.03
        if dist_vwap < -0.60:
            s_call, l_call = round(current_price * (1+dist)), round(current_price * (1+dist) + 20)
            print(f"🟠 ESCENARIO C: BEAR CALL SPREAD | V {s_call} / C {l_call}")
        else:
            s_put, l_put = round(current_price * (1-dist)), round(current_price * (1-dist) - 20)
            print(f"🟠 ESCENARIO C: BULL PUT SPREAD | V {s_put} / C {l_put}")
        print("CONFIG: 10 Contratos | Alas 20 pts | Margen: $20.000")

    elif 18 <= sent['vix1d'] <= 25:
        dist = 0.02
        if abs(dist_vwap) > 0.40:
            if dist_vwap > 0:
                s_put, l_put = round(current_price * (1-dist)), round(current_price * (1-dist) - 10)
                print(f"🟡 ESCENARIO B: BULL PUT SPREAD | V {s_put} / C {l_put}")
            else:
                s_call, l_call = round(current_price * (1+dist)), round(current_price * (1+dist) + 10)
                print(f"🟡 ESCENARIO B: BEAR CALL SPREAD | V {s_call} / C {l_call}")
        else:
            sc, lc = round(current_price * 1.02), round(current_price * 1.02 + 10)
            sp, lp = round(current_price * 0.98), round(current_price * 0.98 - 10)
            print(f"🟡 ESCENARIO B: IRON CONDOR | P {lp}/{sp} -- C {sc}/{lc}")
        print("CONFIG: 10 Contratos | Alas 10 pts | Margen: $10.000")

    else:
        sc, lc = round(current_price * 1.01), round(current_price * 1.01 + 10)
        sp, lp = round(current_price * 0.99), round(current_price * 0.99 - 10)
        print(f"🟢 ESCENARIO A: IRON CONDOR | P {lp}/{sp} -- C {sc}/{lc}")
        print("CONFIG: 5 Contratos | Alas 10 pts | Margen: $5.000")

    print(f"{'='*60}\n")

if __name__ == "__main__":
    analyze_master_strategy()
