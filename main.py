import asyncio
from datetime import datetime, timezone
import os
import time
from aiohttp import web
import ccxt.async_support as ccxt
import pandas as pd
import requests

# ==========================================
# CREDENCIALES TELEGRAM
# ==========================================
TELEGRAM_TOKEN = "8638598049:AAEcQ2kjt9qM_PywnFTZs-2mY-3O8ahW-B0"
# Destinos a los que se envían todas las alertas: tu chat personal + el canal.
TELEGRAM_CHAT_IDS = ["2118999160", "-1003657412134"]

# ==========================================
# PARÁMETROS (idénticos a los inputs del indicador Pine)
# ==========================================
BB_LENGTH = 20
BB_STD = 2.0
RSI_LENGTH = 14
RSI_OB = 70.0
RSI_OS = 30.0

MAX_SWEEP_BARS = 480   # "Máx. velas para el barrido" (24h en TF 3m)

ATR_LENGTH = 14
MIN_GAP_ATR = 0.40     # "Tamaño mínimo del hueco (x ATR)"
MAX_BAND_ATR = 3.0     # "Banda máx. de validez (x ATR)"
MAX_WAIT_FVG = 960     # "Máx. velas esperando FVG / llenado"

# --- Take Profit: dinámico por ATR, igual que el SL ---
# Antes era un 1% fijo (tu regla personal a 10x). Ahora se calcula como
# TP_ATR_MULT veces el ATR, para poder sacar más recorrido en momentos de
# volatilidad Fuerte/Extrema en vez de cortar siempre igual. OJO: esto
# significa que el % de ganancia por operación (y por tanto el % sobre tu
# margen a 10x) ya NO será siempre el mismo — variará según la volatilidad
# del momento, en vez de ser un 10% de margen fijo como con el 1% fijo.
TP_MODE = "atr"        # "atr" = dinámico (recomendado) | "fixed" = % fijo (comportamiento anterior)
TP_ATR_MULT = 1.0      # con SL_ATR_MULT=2.0 esto da una relación 1:2 recompensa:riesgo
TP_PCT = 1.0           # solo se usa si TP_MODE = "fixed"

# --- Stop Loss: dinámico por ATR en vez de % fijo ---
# El SL se calcula como SL_ATR_MULT veces el ATR del momento, en vez de un
# % fijo del precio. Así se adapta al "ruido" normal de cada moneda: una
# moneda tranquila tendrá un SL más ajustado en precio, una muy volátil
# uno más ancho, en vez del mismo 5% para todas.
SL_MODE = "atr"        # "atr" = dinámico (recomendado) | "fixed" = % fijo (comportamiento anterior)
SL_ATR_MULT = 2.0      # punto de partida razonable; ajustar con el backtest
SL_PCT = 5.0           # solo se usa si SL_MODE = "fixed"

BODY_MIN_RATIO = 0.50   # la vela de barrido debe tener cuerpo >= 50% de su rango total

# La vela que rompe Bandas de Bollinger + RSI debe tener un rango mínimo,
# como % del precio, para considerarse una vela de expansión válida.
SIGNAL_MIN_RANGE_PCT = 1.5

# --- Filtro de tendencia de BTC (4h) ---
# Solo se toman largos si BTC está en tendencia alcista, y cortos si está
# en tendencia bajista, para evitar ir contra la marea general del mercado.
BTC_TREND_ENABLED = True
BTC_TREND_SYMBOL = "BTC/USDT"
BTC_TREND_TIMEFRAME = "4h"
BTC_TREND_EMA_LENGTH = 50
BTC_TREND_REFRESH_SECONDS = 900   # cada 15 min es de sobra para un indicador de 4h

# Estado global de la tendencia de BTC, se actualiza en segundo plano.
btc_trend_state = {"trend": None, "last_update": 0}

TIMEFRAME = "3m"
BAR_MS = 3 * 60 * 1000   # duración de una vela de 3m en milisegundos
FETCH_LIMIT = 1000       # velas de histórico a pedir cada ciclo
POST_CLOSE_DELAY = 8     # segundos de margen tras el cierre de vela antes de pedir datos
MAX_CONCURRENT_FETCHES = 15   # peticiones simultáneas a Binance (evita rate-limit)

# Emoji de dirección: se usa en todas las alertas de Telegram para ver de un vistazo
# si la operación es LONG (verde) o SHORT (roja).
DIR_EMOJI = {"long": "🟢", "short": "🔴"}

# ==========================================
# VOLATILIDAD DE LA MONEDA
# ==========================================
# Tamaño medio de las velas (rango high-low como % del precio) en una ventana
# reciente, clasificado en los 4 niveles observados en el backtest:
# Estable (<0.5%), Normal (0.5-1%), Fuerte (1-2%), Extrema (>=2%).
VOLATILITY_LENGTH = 20


def classify_volatility(pct):
    if pct < 0.5:
        return "Estable"
    elif pct < 1.0:
        return "Normal"
    elif pct < 2.0:
        return "Fuerte"
    else:
        return "Extrema"

SYMBOLS = list(set([
    "BTC/USDT", "ETH/USDT", "SOL/USDT", "BNB/USDT", "XRP/USDT", "ADA/USDT",
    "AVAX/USDT", "DOGE/USDT", "DOT/USDT", "LINK/USDT", "NEAR/USDT", "SUI/USDT",
    "PEPE/USDT", "SHIB/USDT", "LTC/USDT", "UNI/USDT", "APT/USDT", "BCH/USDT",
    "ICP/USDT", "FET/USDT", "RENDER/USDT", "ETC/USDT", "FIL/USDT", "XMR/USDT",
    "TIA/USDT", "ATOM/USDT", "STX/USDT", "INJ/USDT", "WIF/USDT", "OP/USDT",
    "ARB/USDT", "THETA/USDT", "GRT/USDT", "RUNE/USDT", "FTM/USDT", "SEI/USDT",
    "FLOKI/USDT", "BONK/USDT", "JUP/USDT", "AAVE/USDT", "MKR/USDT", "ORDI/USDT",
    "EGLD/USDT", "SAND/USDT", "EOS/USDT", "MANA/USDT", "XTZ/USDT", "ALGO/USDT",
    "FLOW/USDT", "AXS/USDT", "GALA/USDT", "SNX/USDT", "NEO/USDT", "KAVA/USDT",
    "ROSE/USDT", "CHZ/USDT", "IOTA/USDT", "MINA/USDT", "COMP/USDT", "CRV/USDT",
    "ZEC/USDT", "KSM/USDT", "DASH/USDT", "1INCH/USDT", "ENJ/USDT", "BAT/USDT",
    "WOO/USDT", "GMT/USDT", "LRC/USDT", "DYDX/USDT", "CFX/USDT", "CKB/USDT",
    "AR/USDT", "BLUR/USDT", "ARKM/USDT", "STRK/USDT", "ENA/USDT", "TNSR/USDT",
    "W/USDT", "OM/USDT", "BOME/USDT", "NOT/USDT", "IO/USDT", "ZK/USDT",
    "ZRO/USDT", "TURBO/USDT", "LISTA/USDT", "DOGS/USDT", "CATI/USDT", "HMSTR/USDT",
    "EIGEN/USDT", "NEIRO/USDT", "MEW/USDT", "MEME/USDT", "BEAM/USDT", "RONIN/USDT",
    "PIXEL/USDT", "ALT/USDT", "MANTA/USDT", "XAI/USDT", "ACE/USDT", "NFP/USDT",
    "AI/USDT", "PORTAL/USDT", "AEVO/USDT", "ETHFI/USDT", "SAGA/USDT", "OMNI/USDT",
    "REZ/USDT", "BB/USDT", "BANANA/USDT", "SYN/USDT", "PENDLE/USDT", "CELO/USDT",
    "ONE/USDT", "HOT/USDT", "ZIL/USDT", "RVN/USDT", "ANKR/USDT", "AUDIO/USDT",
    "LDO/USDT", "STORJ/USDT", "SKL/USDT", "ICX/USDT", "ZRX/USDT", "ONT/USDT",
    "WAXP/USDT", "SPELL/USDT", "SLP/USDT", "ALPHA/USDT", "COTI/USDT", "ZEN/USDT",
    "STRAX/USDT", "SXP/USDT", "C98/USDT", "CHR/USDT", "OXT/USDT", "NMR/USDT",
    "TRB/USDT", "BAND/USDT", "RLC/USDT", "API3/USDT", "TRU/USDT", "BADGER/USDT",
    "POND/USDT", "PERP/USDT", "ALICE/USDT", "SUPER/USDT", "UNFI/USDT", "LIT/USDT",
    "SFP/USDT", "DODO/USDT", "BEL/USDT", "CTSI/USDT", "DAR/USDT", "MOVR/USDT",
    "SYS/USDT", "PEOPLE/USDT", "ACH/USDT", "AGLD/USDT", "GLMR/USDT", "ASTR/USDT",
    "BSW/USDT", "CVX/USDT", "FIS/USDT", "STPT/USDT", "RAD/USDT", "T/USDT",
    "PROS/USDT", "VTHO/USDT", "WRX/USDT", "MBL/USDT", "DENT/USDT", "KEY/USDT",
    "TWT/USDT", "COS/USDT", "CTXC/USDT", "HBAR/USDT", "0G/USDT", "1000BONK/USDT",
    "1000PEPE/USDT", "ACU/USDT", "AERO/USDT", "AIA/USDT", "AKE/USDT", "APE/USDT",
    "ASR/USDT", "ASTER/USDT", "ATH/USDT", "AVNT/USDT", "BANK/USDT", "BEAT/USDT",
    "BIO/USDT", "BROCCOLIF3B/USDT", "BSV/USDT", "B/USDT", "CAKE/USDT", "CC/USDT",
    "CELR/USDT", "CHIP/USDT", "COAI/USDT", "DEXE/USDT", "DIA/USDT", "ELSA/USDT",
    "ENS/USDT", "FARTCOIN/USDT", "FF/USDT", "FIGHT/USDT", "FLUX/USDT", "FOGO/USDT",
    "GENIUS/USDT", "GIGGLE/USDT", "GMX/USDT", "GRASS/USDT", "GRIFFAIN/USDT", "GUN/USDT",
    "GWEI/USDT", "H/USDT", "HYPE/USDT", "ICNT/USDT", "ID/USDT", "INX/USDT",
    "JASMY/USDT", "JOE/USDT", "JTO/USDT", "KAS/USDT", "KAT/USDT", "KITE/USDT",
    "LAYER/USDT", "MANTRA/USDT", "METIS/USDT", "MET/USDT", "MON/USDT", "MORPHO/USDT",
    "MUBARAK/USDT", "NIGHT/USDT", "OG/USDT", "ONDO/USDT", "PENGU/USDT", "PLUME/USDT",
    "POL/USDT", "PUMP/USDT", "QNT/USDT", "Q/USDT", "RAYSOL/USDT", "RIVER/USDT",
    "SAFE/USDT", "SCRT/USDT", "SHELL/USDT", "SKR/USDT", "SKYAI/USDT", "SKY/USDT",
    "SOON/USDT", "SPORTFUN/USDT", "SPX/USDT", "SSV/USDT", "SYRUP/USDT", "TAO/USDT",
    "THE/USDT", "TRIA/USDT", "TRUMP/USDT", "TRX/USDT", "UB/USDT", "VET/USDT",
    "VIRTUAL/USDT", "WLD/USDT", "WLFI/USDT", "XLM/USDT", "XPL/USDT", "XVG/USDT",
    "ZAMA/USDT"
]))

exchange = ccxt.binance({"enableRateLimit": True, "options": {"defaultType": "swap"}})

# Estado persistente por símbolo (equivalente a las variables "var" de Pine)
symbol_state = {}


def default_state():
    return {
        "initialized": False,
        "last_time": None,      # timestamp de la última vela procesada
        "state": "idle",        # idle -> sweep -> fvg -> wait_fill -> filled
        "dir": None,
        "sig_price": None,
        "sig_high": None,
        "sig_low": None,
        "sig_time": None,
        "extreme_favor": None,
        "sig_volatility_pct": None,
        "sig_volatility_label": None,
        "sig_range_pct": None,
        "sweep_time": None,
        "gap_top": None,
        "gap_bottom": None,
        "entry_price": None,
        "tp_price": None,
        "sl_price": None,
    }


def fmt_time(bar_time_ms):
    return datetime.fromtimestamp(bar_time_ms / 1000, tz=timezone.utc).strftime("%H:%M UTC")


async def update_btc_trend():
    """Descarga velas de BTC en 4h y actualiza btc_trend_state con
    'alcista' o 'bajista' según el cierre esté por encima o por debajo
    de su EMA de BTC_TREND_EMA_LENGTH periodos."""
    if not BTC_TREND_ENABLED:
        return
    now = time.time()
    if now - btc_trend_state["last_update"] < BTC_TREND_REFRESH_SECONDS:
        return
    try:
        bars = await exchange.fetch_ohlcv(
            BTC_TREND_SYMBOL, timeframe=BTC_TREND_TIMEFRAME, limit=BTC_TREND_EMA_LENGTH + 10
        )
        if not bars or len(bars) < BTC_TREND_EMA_LENGTH + 1:
            return
        closes = pd.Series([b[4] for b in bars])
        ema = closes.ewm(span=BTC_TREND_EMA_LENGTH, adjust=False).mean()
        trend = "alcista" if closes.iloc[-1] > ema.iloc[-1] else "bajista"
        btc_trend_state["trend"] = trend
        btc_trend_state["last_update"] = now
    except Exception as e:
        print(f"Error actualizando tendencia BTC: {e}", flush=True)


def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    for chat_id in TELEGRAM_CHAT_IDS:
        try:
            requests.post(url, json={"chat_id": chat_id, "text": message, "parse_mode": "Markdown"}, timeout=10)
        except Exception as e:
            print(f"Error Telegram ({chat_id}): {e}", flush=True)


def compute_indicators(df):
    df["basis"] = df["close"].rolling(BB_LENGTH).mean()
    df["dev"] = BB_STD * df["close"].rolling(BB_LENGTH).std(ddof=0)
    df["upper_bb"] = df["basis"] + df["dev"]
    df["lower_bb"] = df["basis"] - df["dev"]

    # RSI estilo Wilder/RMA (igual que ta.rsi en Pine)
    delta = df["close"].diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)
    alpha = 1 / RSI_LENGTH
    avg_gain = gain.ewm(alpha=alpha, min_periods=RSI_LENGTH, adjust=False).mean()
    avg_loss = loss.ewm(alpha=alpha, min_periods=RSI_LENGTH, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, float("nan"))
    df["rsi"] = 100 - (100 / (1 + rs))
    df["rsi"] = df["rsi"].fillna(100)

    # ATR estilo Wilder/RMA (igual que ta.atr en Pine, NO media simple)
    prev_close = df["close"].shift(1)
    tr = pd.concat([
        df["high"] - df["low"],
        (df["high"] - prev_close).abs(),
        (df["low"] - prev_close).abs(),
    ], axis=1).max(axis=1)
    df["atr"] = tr.ewm(alpha=1 / ATR_LENGTH, min_periods=ATR_LENGTH, adjust=False).mean()

    # Volatilidad: tamaño medio de vela (rango high-low) como % del precio de cierre
    df["candle_range_pct"] = (df["high"] - df["low"]) / df["close"] * 100
    df["volatility_pct"] = df["candle_range_pct"].rolling(VOLATILITY_LENGTH).mean()

    return df


def process_bar(symbol, i, df, st, alert_enabled):
    """Procesa UNA vela replicando exactamente los bloques del script Pine,
    en el mismo orden (no son excluyentes entre sí, igual que en Pine)."""
    row = df.iloc[i]
    open_, close, high, low = row["open"], row["close"], row["high"], row["low"]
    rsi, upper_bb, lower_bb, atr = row["rsi"], row["upper_bb"], row["lower_bb"], row["atr"]
    volatility_pct = row["volatility_pct"]
    bar_time = row["time"]

    if pd.isna(rsi) or pd.isna(upper_bb) or pd.isna(lower_bb) or pd.isna(atr) or pd.isna(volatility_pct):
        st["last_time"] = bar_time
        return

    body_size = abs(close - open_)
    candle_range = high - low
    body_ratio = (body_size / candle_range) if candle_range > 0 else 0.0

    # La vela que rompe Bandas de Bollinger + RSI debe tener un tamaño
    # mínimo (rango como % del precio) para considerarse señal válida.
    candle_range_pct = row["candle_range_pct"]
    is_expansion_candle = candle_range_pct >= SIGNAL_MIN_RANGE_PCT

    # La tendencia de BTC se calcula y se muestra en las alertas, pero NO
    # bloquea ninguna señal: se mandan tanto longs como shorts sin importar
    # hacia dónde vaya BTC.
    signal_long = close < lower_bb and rsi < RSI_OS and is_expansion_candle
    signal_short = close > upper_bb and rsi > RSI_OB and is_expansion_candle

    # --- 1) Nueva señal (solo si no hay operación en curso) ---
    if st["state"] == "idle" and (signal_long or signal_short):
        st["dir"] = "long" if signal_long else "short"
        st["sig_time"] = bar_time
        st["sig_high"] = high
        st["sig_low"] = low
        st["sig_price"] = close
        st["extreme_favor"] = high if st["dir"] == "long" else low
        st["sig_volatility_pct"] = volatility_pct
        st["sig_volatility_label"] = classify_volatility(volatility_pct)
        st["sig_range_pct"] = candle_range_pct
        st["state"] = "sweep"

    # --- 2) Esperando barrido de liquidez ---
    if st["state"] == "sweep":
        elapsed = round((bar_time - st["sig_time"]) / BAR_MS)
        if elapsed > MAX_SWEEP_BARS:
            st["state"] = "idle"
        else:
            if st["dir"] == "long":
                sweep_cond = (
                    close < st["sig_low"]        # cierra por debajo del extremo de la señal
                    and close < open_             # vela bajista (cuerpo a favor del barrido)
                    and body_ratio >= BODY_MIN_RATIO   # con cuerpo real, no doji
                )
            else:
                sweep_cond = (
                    close > st["sig_high"]
                    and close > open_             # vela alcista
                    and body_ratio >= BODY_MIN_RATIO
                )
            if sweep_cond:
                st["sweep_time"] = bar_time
                st["state"] = "fvg"
                if alert_enabled:
                    emoji = DIR_EMOJI[st["dir"]]
                    send_telegram(
                        f"🧲 *Barrido de liquidez* {emoji}\n"
                        f"Par: `{symbol}`\n"
                        f"Dirección: *{st['dir'].upper()}*\n"
                        f"Precio: `{close:.6f}`\n"
                        f"📊 Volatilidad: *{st['sig_volatility_label']}* ({st['sig_volatility_pct']:.2f}%)\n"
                        f"🩻 Diagnóstico → vela señal: {st['sig_range_pct']:.2f}% rango | vela barrido: {body_ratio*100:.0f}% cuerpo\n"
                        f"Buscando FVG..."
                    )

    # --- 3) Esperando el primer FVG válido a favor ---
    if st["state"] == "fvg":
        if st["dir"] == "long":
            st["extreme_favor"] = max(st["extreme_favor"], high)
            favor_atr = (st["extreme_favor"] - st["sig_price"]) / atr
        else:
            st["extreme_favor"] = min(st["extreme_favor"], low)
            favor_atr = (st["sig_price"] - st["extreme_favor"]) / atr

        elapsed = round((bar_time - st["sweep_time"]) / BAR_MS)

        if MAX_BAND_ATR is not None and favor_atr > MAX_BAND_ATR:
            st["state"] = "idle"   # se fue >3 ATR a favor antes de formar el hueco -> cancelado
            if alert_enabled:
                emoji = DIR_EMOJI[st["dir"]]
                send_telegram(
                    f"❌ *Señal cancelada — se alejó demasiado* {emoji}\n"
                    f"Par: `{symbol}`\n"
                    f"Dirección: *{st['dir'].upper()}*\n"
                    f"El precio se movió {favor_atr:.2f}x ATR a favor (límite: {MAX_BAND_ATR}x) sin formar un FVG limpio."
                )
        elif elapsed > MAX_SWEEP_BARS:
            st["state"] = "idle"
        elif i >= 2 and df["time"].iloc[i - 2] >= st["sweep_time"]:
            high2 = df["high"].iloc[i - 2]
            low2 = df["low"].iloc[i - 2]
            bull_fvg = st["dir"] == "long" and low > high2
            bear_fvg = st["dir"] == "short" and high < low2
            if bull_fvg or bear_fvg:
                # Primer FVG que se forma tras el barrido: se acepta directamente,
                # sin exigir tamaño mínimo ni distancia máxima al precio de la señal.
                g_top = low if st["dir"] == "long" else low2
                g_bot = high2 if st["dir"] == "long" else high
                g_mid = (g_top + g_bot) / 2
                st["gap_top"] = g_top
                st["gap_bottom"] = g_bot
                st["entry_price"] = g_mid
                if TP_MODE == "atr":
                    tp_distance = TP_ATR_MULT * atr
                    st["tp_price"] = g_mid + tp_distance if st["dir"] == "long" else g_mid - tp_distance
                else:
                    st["tp_price"] = g_mid * (1 + TP_PCT / 100) if st["dir"] == "long" else g_mid * (1 - TP_PCT / 100)
                if SL_MODE == "atr":
                    sl_distance = SL_ATR_MULT * atr
                    st["sl_price"] = g_mid - sl_distance if st["dir"] == "long" else g_mid + sl_distance
                else:
                    st["sl_price"] = g_mid * (1 - SL_PCT / 100) if st["dir"] == "long" else g_mid * (1 + SL_PCT / 100)
                st["state"] = "wait_fill"
                gap_size_atr = abs(g_top - g_bot) / atr
                if alert_enabled:
                    emoji = DIR_EMOJI[st["dir"]]
                    send_telegram(
                        f"📌 *Señal de entrada — FVG formado* {emoji}\n"
                        f"Par: `{symbol}`\n"
                        f"Dirección: *{st['dir'].upper()}*\n"
                        f"📊 Volatilidad: *{st['sig_volatility_label']}* ({st['sig_volatility_pct']:.2f}%)\n"
                        f"₿ Tendencia BTC 4h: *{btc_trend_state['trend'] or 'sin datos'}*\n"
                        f"🩻 Diagnóstico → vela señal: {st['sig_range_pct']:.2f}% rango | hueco FVG: {gap_size_atr:.2f}x ATR\n"
                        f"📍 Entrada límite (50% FVG): `{st['entry_price']:.6f}`\n"
                        f"🎯 TP: `{st['tp_price']:.6f}`\n"
                        f"🛑 SL: `{st['sl_price']:.6f}`"
                    )

    # --- 4) Esperando el llenado de la entrada límite ---
    if st["state"] == "wait_fill":
        elapsed = round((bar_time - st["sweep_time"]) / BAR_MS)
        if elapsed > MAX_WAIT_FVG:
            st["state"] = "idle"
        else:
            filled = low <= st["entry_price"] if st["dir"] == "long" else high >= st["entry_price"]
            if filled:
                st["state"] = "filled"
                # (sin alerta aquí para no saturar Telegram; el estado se sigue registrando)

    # --- 5) En operación: salida al primer toque de TP o SL ---
    if st["state"] == "filled":
        hit_tp = high >= st["tp_price"] if st["dir"] == "long" else low <= st["tp_price"]
        hit_sl = low <= st["sl_price"] if st["dir"] == "long" else high >= st["sl_price"]
        if hit_tp or hit_sl:
            won = hit_tp and not hit_sl
            # (sin alerta aquí para no saturar Telegram; el estado se sigue registrando)
            st["state"] = "idle"

    st["last_time"] = bar_time


async def run_symbol(symbol, semaphore):
    async with semaphore:
        try:
            bars = await exchange.fetch_ohlcv(symbol, timeframe=TIMEFRAME, limit=FETCH_LIMIT)
            if not bars or len(bars) < BB_LENGTH + ATR_LENGTH + 5:
                return
            # Se descarta la última vela porque aún está en formación (no cerrada)
            df = pd.DataFrame(bars, columns=["time", "open", "high", "low", "close", "volume"]).iloc[:-1].copy()
            df = compute_indicators(df)

            st = symbol_state.setdefault(symbol, default_state())

            if not st["initialized"]:
                # Primera vez que vemos este símbolo: reconstruimos en qué estado
                # está AHORA MISMO sin mandar alertas de todo el histórico.
                for i in range(len(df)):
                    process_bar(symbol, i, df, st, alert_enabled=False)
                st["initialized"] = True
            else:
                new_rows = df[df["time"] > st["last_time"]]
                if new_rows.empty:
                    return
                start_idx = new_rows.index[0]
                for i in range(start_idx, len(df)):
                    process_bar(symbol, i, df, st, alert_enabled=True)

        except Exception as e:
            print(f"Error en {symbol}: {e}", flush=True)


async def bucle_bot():
    send_telegram("🚀 *Bot FVG V3 iniciado* (réplica fiel del indicador Pine)\nSincronizando estado inicial de todos los pares...")
    semaphore = asyncio.Semaphore(MAX_CONCURRENT_FETCHES)
    while True:
        now = datetime.now(timezone.utc)
        sleep_time = (180 - ((now.minute % 3) * 60 + now.second)) + POST_CLOSE_DELAY
        if sleep_time < 5:
            sleep_time += 180
        await asyncio.sleep(sleep_time)
        await update_btc_trend()
        tasks = [run_symbol(symbol, semaphore) for symbol in SYMBOLS]
        await asyncio.gather(*tasks, return_exceptions=True)


async def handle_ping(request):
    return web.Response(text="Bot FVG V3 (réplica Pine) activo")


async def main():
    app = web.Application()
    app.router.add_get("/", handle_ping)
    runner = web.AppRunner(app)
    await runner.setup()
    await web.TCPSite(runner, "0.0.0.0", int(os.environ.get("PORT", 10000))).start()
    asyncio.create_task(bucle_bot())
    try:
        while True:
            await asyncio.sleep(3600)
    finally:
        await exchange.close()


if __name__ == "__main__":
    asyncio.run(main())
