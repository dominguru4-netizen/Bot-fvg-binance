import asyncio
from datetime import datetime, timezone
import os
from aiohttp import web
import ccxt.async_support as ccxt
import pandas as pd
import requests

# ==========================================
# CREDENCIALES TELEGRAM
# ==========================================
TELEGRAM_TOKEN = "8638598049:AAEcQ2kjt9qM_PywnFTZs-2mY-3O8ahW-B0"
TELEGRAM_CHAT_ID = "2118999160"

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

TP_PCT = 4.0
SL_PCT = 3.0

BODY_MIN_RATIO = 0.30   # la vela de barrido debe tener cuerpo >= 30% de su rango total

TIMEFRAME = "3m"
BAR_MS = 3 * 60 * 1000   # duración de una vela de 3m en milisegundos
FETCH_LIMIT = 1000       # velas de histórico a pedir cada ciclo
POST_CLOSE_DELAY = 8     # segundos de margen tras el cierre de vela antes de pedir datos
MAX_CONCURRENT_FETCHES = 15   # peticiones simultáneas a Binance (evita rate-limit)

# Emoji de dirección: se usa en todas las alertas de Telegram para ver de un vistazo
# si la operación es LONG (verde) o SHORT (roja).
DIR_EMOJI = {"long": "🟢", "short": "🔴"}

SYMBOLS = list(set([
    "BTC/USDT", "ETH/USDT", "SOL/USDT", "BNB/USDT", "XRP/USDT", "ADA/USDT",
    "AVAX/USDT", "DOGE/USDT", "DOT/USDT", "LINK/USDT", "NEAR/USDT", "SUI/USDT", "PEPE/USDT", "SHIB/USDT",
    "LTC/USDT", "UNI/USDT", "APT/USDT", "BCH/USDT", "ICP/USDT", "FET/USDT", "RENDER/USDT", "ETC/USDT",
    "FIL/USDT", "XMR/USDT", "TIA/USDT", "ATOM/USDT", "STX/USDT", "INJ/USDT", "WIF/USDT", "OP/USDT",
    "ARB/USDT", "THETA/USDT", "GRT/USDT", "RUNE/USDT", "FTM/USDT", "SEI/USDT", "FLOKI/USDT", "BONK/USDT",
    "JUP/USDT", "AAVE/USDT", "MKR/USDT", "ORDI/USDT", "EGLD/USDT", "SAND/USDT", "EOS/USDT", "MANA/USDT",
    "XTZ/USDT", "ALGO/USDT", "FLOW/USDT", "AXS/USDT", "GALA/USDT", "SNX/USDT", "NEO/USDT", "KAVA/USDT",
    "ROSE/USDT", "CHZ/USDT", "IOTA/USDT", "MINA/USDT", "COMP/USDT", "CRV/USDT", "ZEC/USDT", "KSM/USDT",
    "DASH/USDT", "1INCH/USDT", "ENJ/USDT", "BAT/USDT", "WOO/USDT", "GMT/USDT", "LRC/USDT", "DYDX/USDT",
    "CFX/USDT", "CKB/USDT", "AR/USDT", "BLUR/USDT", "ARKM/USDT", "STRK/USDT", "ENA/USDT", "TNSR/USDT",
    "W/USDT", "OM/USDT", "BOME/USDT", "NOT/USDT", "IO/USDT", "ZK/USDT", "ZRO/USDT", "TURBO/USDT",
    "LISTA/USDT", "DOGS/USDT", "CATI/USDT", "HMSTR/USDT", "EIGEN/USDT", "NEIRO/USDT", "MEW/USDT",
    "MEME/USDT", "BEAM/USDT", "RONIN/USDT", "PIXEL/USDT", "ALT/USDT", "MANTA/USDT", "XAI/USDT",
    "ACE/USDT", "NFP/USDT", "AI/USDT", "PORTAL/USDT", "AEVO/USDT", "ETHFI/USDT", "SAGA/USDT", "OMNI/USDT",
    "REZ/USDT", "BB/USDT", "BANANA/USDT", "SYN/USDT", "PENDLE/USDT", "CELO/USDT", "ONE/USDT", "HOT/USDT",
    "ZIL/USDT", "RVN/USDT", "ANKR/USDT", "AUDIO/USDT", "LDO/USDT", "STORJ/USDT", "SKL/USDT", "ICX/USDT",
    "ZRX/USDT", "ONT/USDT", "WAXP/USDT", "SPELL/USDT", "SLP/USDT", "ALPHA/USDT", "COTI/USDT", "ZEN/USDT",
    "STRAX/USDT", "SXP/USDT", "C98/USDT", "CHR/USDT", "OXT/USDT", "NMR/USDT", "TRB/USDT", "BAND/USDT",
    "RLC/USDT", "API3/USDT", "TRU/USDT", "BADGER/USDT", "POND/USDT", "PERP/USDT", "ALICE/USDT", "SUPER/USDT",
    "UNFI/USDT", "LIT/USDT", "SFP/USDT", "DODO/USDT", "BEL/USDT", "CTSI/USDT", "DAR/USDT", "MOVR/USDT",
    "SYS/USDT", "PEOPLE/USDT", "ACH/USDT", "AGLD/USDT", "GLMR/USDT", "ASTR/USDT", "BSW/USDT", "CVX/USDT",
    "FIS/USDT", "STPT/USDT", "RAD/USDT", "T/USDT", "PROS/USDT", "VTHO/USDT", "WRX/USDT", "MBL/USDT",
    "DENT/USDT", "KEY/USDT", "TWT/USDT", "COS/USDT", "CTXC/USDT", "HBAR/USDT"
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
        "sweep_time": None,
        "gap_top": None,
        "gap_bottom": None,
        "entry_price": None,
        "tp_price": None,
        "sl_price": None,
    }


def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try:
        requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown"}, timeout=10)
    except Exception as e:
        print(f"Error Telegram: {e}", flush=True)


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

    return df


def process_bar(symbol, i, df, st, alert_enabled):
    """Procesa UNA vela replicando exactamente los bloques del script Pine,
    en el mismo orden (no son excluyentes entre sí, igual que en Pine)."""
    row = df.iloc[i]
    open_, close, high, low = row["open"], row["close"], row["high"], row["low"]
    rsi, upper_bb, lower_bb, atr = row["rsi"], row["upper_bb"], row["lower_bb"], row["atr"]
    bar_time = row["time"]

    if pd.isna(rsi) or pd.isna(upper_bb) or pd.isna(lower_bb) or pd.isna(atr):
        st["last_time"] = bar_time
        return

    body_size = abs(close - open_)
    candle_range = high - low
    body_ratio = (body_size / candle_range) if candle_range > 0 else 0.0

    signal_long = close < lower_bb and rsi < RSI_OS
    signal_short = close > upper_bb and rsi > RSI_OB

    # --- 1) Nueva señal (solo si no hay operación en curso) ---
    if st["state"] == "idle" and (signal_long or signal_short):
        st["dir"] = "long" if signal_long else "short"
        st["sig_time"] = bar_time
        st["sig_high"] = high
        st["sig_low"] = low
        st["sig_price"] = close
        st["extreme_favor"] = high if st["dir"] == "long" else low
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

        if favor_atr > MAX_BAND_ATR:
            st["state"] = "idle"   # se fue >3 ATR a favor antes de formar el hueco -> cancelado
        elif elapsed > MAX_SWEEP_BARS:
            st["state"] = "idle"
        elif i >= 2:
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
                st["tp_price"] = g_mid * (1 + TP_PCT / 100) if st["dir"] == "long" else g_mid * (1 - TP_PCT / 100)
                st["sl_price"] = g_mid * (1 - SL_PCT / 100) if st["dir"] == "long" else g_mid * (1 + SL_PCT / 100)
                st["state"] = "wait_fill"
                if alert_enabled:
                    emoji = DIR_EMOJI[st["dir"]]
                    send_telegram(
                        f"📌 *Señal de entrada — FVG formado* {emoji}\n"
                        f"Par: `{symbol}`\n"
                        f"Dirección: *{st['dir'].upper()}*\n"
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
