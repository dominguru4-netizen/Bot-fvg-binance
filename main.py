import asyncio
from datetime import datetime, timezone
import os
from aiohttp import web
import ccxt
import pandas as pd
import requests

# ==========================================
# CREDENCIALES TELEGRAM
# ==========================================
TELEGRAM_TOKEN = "8638598049:AAEcQ2kjt9qM_PywnFTZs-2mY-3O8ahW-B0"
TELEGRAM_CHAT_ID = "2118999160"

# ==========================================
# PARÁMETROS GLOBALES (ESTRATEGIA FVG V3)
# ==========================================
BB_LENGTH = 20
BB_STD = 2.0
RSI_LENGTH = 14
RSI_OVERBOUGHT = 65
RSI_OVERSOLD = 35

MAX_VALIDEZ_ATR = 3.0    # Regla 4: Cancelación si el precio supera 3 ATR
MIN_GAP_ATR = 0.0        # Solicitado: Tamaño de FVG mínimo en 0 (acepta cualquier FVG > 0)
LOOKBACK_BARS = 60       # Ventana de rastreo (máximo 24h equivaldría a más, pero 60 velas de 3m es suficiente para setups activos)

TP_PERCENT = 0.040       # Configuración óptima del documento V3: +4% TP
SL_PERCENT = 0.030       # Configuración óptima del documento V3: -3% SL

sent_signals = set()

SYMBOLS = list(set([
    # --- Lista Original ---
    "H/USDT", "SKYAI/USDT", "BTC/USDT", "ETH/USDT", "SOL/USDT", "BNB/USDT", "XRP/USDT", "ADA/USDT", 
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
    "DENT/USDT", "KEY/USDT", "TWT/USDT", "COS/USDT", "CTXC/USDT",
    
    # --- Lista Nueva ---
    "0G/USDT", "1000BONK/USDT", "1000PEPE/USDT", "AAVE/USDT", "ACU/USDT", "ADA/USDT",
    "AERO/USDT", "AIA/USDT", "AKE/USDT", "ALGO/USDT", "APE/USDT", "APT/USDT", "ARB/USDT",
    "ASR/USDT", "ASTER/USDT", "ATH/USDT", "ATOM/USDT", "AVAX/USDT", "AVNT/USDT", "BANK/USDT",
    "BB/USDT", "BEAT/USDT", "BIO/USDT", "BNB/USDT", "BOME/USDT", "BROCCOLIF3B/USDT", "BSV/USDT",
    "BTC/USDT", "B/USDT", "C98/USDT", "CAKE/USDT", "CC/USDT", "CELR/USDT", "CHIP/USDT", "CHR/USDT",
    "CHZ/USDT", "COAI/USDT", "CRV/USDT", "DASH/USDT", "DEXE/USDT", "DIA/USDT", "DOT/USDT",
    "DYDX/USDT", "EIGEN/USDT", "ELSA/USDT", "ENS/USDT", "ETC/USDT", "ETHFI/USDT", "ETH/USDT",
    "FARTCOIN/USDT", "FF/USDT", "FIGHT/USDT", "FIL/USDT", "FLUX/USDT", "FOGO/USDT", "GENIUS/USDT",
    "GIGGLE/USDT", "GMX/USDT", "GRASS/USDT", "GRIFFAIN/USDT", "GRT/USDT", "GUN/USDT", "GWEI/USDT",
    "HBAR/USDT", "H/USDT", "HYPE/USDT", "ICNT/USDT", "ICP/USDT", "ID/USDT", "INX/USDT", "IOTA/USDT",
    "JASMY/USDT", "JOE/USDT", "JTO/USDT", "JUP/USDT", "KAS/USDT", "KAT/USDT", "KITE/USDT",
    "LAYER/USDT", "LDO/USDT", "LINK/USDT", "LIT/USDT", "LTC/USDT", "MANA/USDT", "MANTRA/USDT",
    "METIS/USDT", "MET/USDT", "MON/USDT", "MORPHO/USDT", "MOVR/USDT", "MUBARAK/USDT", "NEAR/USDT",
    "NIGHT/USDT", "OG/USDT", "ONDO/USDT", "ONE/USDT", "ONT/USDT", "OP/USDT", "PENGU/USDT",
    "PLUME/USDT", "POL/USDT", "PUMP/USDT", "QNT/USDT", "Q/USDT", "RAYSOL/USDT", "RENDER/USDT",
    "RIVER/USDT", "RLC/USDT", "SAFE/USDT", "SAND/USDT", "SCRT/USDT", "SEI/USDT", "SHELL/USDT",
    "SKL/USDT", "SKR/USDT", "SKYAI/USDT", "SKY/USDT", "SOON/USDT", "SPORTFUN/USDT", "SPX/USDT",
    "SSV/USDT", "STRK/USDT", "STX/USDT", "SUI/USDT", "SYRUP/USDT", "TAO/USDT", "THETA/USDT",
    "THE/USDT", "TIA/USDT", "TRB/USDT", "TRIA/USDT", "TRUMP/USDT", "TRX/USDT", "UB/USDT", "UNI/USDT",
    "VET/USDT", "VIRTUAL/USDT", "WAXP/USDT", "WIF/USDT", "WLD/USDT", "WLFI/USDT", "XLM/USDT",
    "XMR/USDT", "XPL/USDT", "XRP/USDT", "XVG/USDT", "ZAMA/USDT", "ZEN/USDT"
]))

exchange = ccxt.binance(
    {"enableRateLimit": True, "options": {"defaultType": "swap"}}
)

def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown",
    }
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"Error Telegram: {e}", flush=True)

def run_fvg_v3_strategy(symbol, timeframe):
    try:
        bars = exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=150)
        if not bars or len(bars) < 120:
            return

        df = pd.DataFrame(
            bars, columns=["time", "open", "high", "low", "close", "volume"]
        )
        # Descartamos la vela actual en formación
        df = df.iloc[:-1].copy()
        n = len(df)

        last_candle_time = df["time"].iloc[-1]
        signal_key = f"{symbol}_{timeframe}_{last_candle_time}"
        if signal_key in sent_signals:
            return

        # --- INDICADORES TÉCNICOS ---
        high_low = df["high"] - df["low"]
        high_close = (df["high"] - df["close"].shift()).abs()
        low_close = (df["low"] - df["close"].shift()).abs()
        true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        df["atr"] = true_range.rolling(window=14).mean()

        df["sma"] = df["close"].rolling(window=BB_LENGTH).mean()
        df["std"] = df["close"].rolling(window=BB_LENGTH).std()
        df["upper_bb"] = df["sma"] + (BB_STD * df["std"])
        df["lower_bb"] = df["sma"] - (BB_STD * df["std"])

        delta = df["close"].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=RSI_LENGTH).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=RSI_LENGTH).mean()
        rs = gain / loss
        df["rsi"] = 100 - (100 / (1 + rs))

        current_close = df["close"].iloc[-1]
        current_atr = df["atr"].iloc[-1]

        # --- EVALUACIÓN DE SECUENCIA V3 ---
        active_direction = "NONE"
        signal_low = float('inf')
        signal_high = -float('inf')
        signal_price = 0.0
        sweep_confirmed = False

        start_idx = max(0, n - LOOKBACK_BARS)

        for i in range(start_idx, n - 2):  # Dejamos espacio para el FVG de 3 velas al final
            # 1. Detección de Señal BOT-S
            is_bots_long = (df['low'].iloc[i] <= df['lower_bb'].iloc[i]) and (df['rsi'].iloc[i] <= RSI_OVERSOLD)
            is_bots_short = (df['high'].iloc[i] >= df['upper_bb'].iloc[i]) and (df['rsi'].iloc[i] >= RSI_OVERBOUGHT)

            if is_bots_long:
                active_direction = "LONG"
                signal_low = df['low'].iloc[i]
                signal_price = df['close'].iloc[i]
                sweep_confirmed = False

            elif is_bots_short:
                active_direction = "SHORT"
                signal_high = df['high'].iloc[i]
                signal_price = df['close'].iloc[i]
                sweep_confirmed = False

            # 2. Barrido de Liquidez (Cierre por debajo/encima de la señal)
            if active_direction == "LONG" and not sweep_confirmed:
                if df['close'].iloc[i] < signal_low:
                    sweep_confirmed = True

            elif active_direction == "SHORT" and not sweep_confirmed:
                if df['close'].iloc[i] > signal_high:
                    sweep_confirmed = True

            # 3. Regla de Cancelación (Si rebasa 3 ATR a favor antes de formar FVG)
            if sweep_confirmed:
                atr_at_i = df['atr'].iloc[i]
                if active_direction == "LONG" and (df['high'].iloc[i] - signal_price) > (3 * atr_at_i):
                    active_direction = "NONE"
                    sweep_confirmed = False
                elif active_direction == "SHORT" and (signal_price - df['low'].iloc[i]) > (3 * atr_at_i):
                    active_direction = "NONE"
                    sweep_confirmed = False

        if not sweep_confirmed or active_direction == "NONE":
            return

        # --- 4. DETECCIÓN DE FVG (ÚLTIMAS 3 VELAS) ---
        v1_high = df["high"].iloc[-3]
        v1_low = df["low"].iloc[-3]
        v3_low = df["low"].iloc[-1]
        v3_high = df["high"].iloc[-1]

        clean_symbol = symbol.replace("/", "") + ".P"

        if active_direction == "LONG":
            fvg_gap = v3_low - v1_high
            fvg_atr_ratio = fvg_gap / current_atr if current_atr > 0 else 0

            # Cumple condición de FVG válido (gap_atr >= 0.0)
            if fvg_gap > 0 and fvg_atr_ratio >= MIN_GAP_ATR:
                fvg_mid = (v1_high + v3_low) / 2.0
                
                # Verificación de banda de validez (dentro de 3 ATR)
                if abs(fvg_mid - signal_price) <= (3 * current_atr):
                    sl = fvg_mid * (1 - SL_PERCENT)
                    tp = fvg_mid * (1 + TP_PERCENT)

                    msg = (
                        f"🟢 *ESTRATEGIA FVG V3 · LONG*\n"
                        f"Par: `{clean_symbol}`\n"
                        f"📍 Entrada Límite (50% FVG): `{fvg_mid:.6f}`\n"
                        f"🎯 TP (+4%): `{tp:.6f}`\n"
                        f"🛑 SL (-3%): `{sl:.6f}`\n"
                        f"Rango Gap/ATR: `{fvg_atr_ratio:.2f}`"
                    )
                    send_telegram(msg)
                    sent_signals.add(signal_key)

        elif active_direction == "SHORT":
            fvg_gap = v1_low - v3_high
            fvg_atr_ratio = fvg_gap / current_atr if current_atr > 0 else 0

            if fvg_gap > 0 and fvg_atr_ratio >= MIN_GAP_ATR:
                fvg_mid = (v1_low + v3_high) / 2.0

                if abs(fvg_mid - signal_price) <= (3 * current_atr):
                    sl = fvg_mid * (1 + SL_PERCENT)
                    tp = fvg_mid * (1 - TP_PERCENT)

                    msg = (
                        f"🔴 *ESTRATEGIA FVG V3 · SHORT*\n"
                        f"Par: `{clean_symbol}`\n"
                        f"📍 Entrada Límite (50% FVG): `{fvg_mid:.6f}`\n"
                        f"🎯 TP (+4%): `{tp:.6f}`\n"
                        f"🛑 SL (-3%): `{sl:.6f}`\n"
                        f"Rango Gap/ATR: `{fvg_atr_ratio:.2f}`"
                    )
                    send_telegram(msg)
                    sent_signals.add(signal_key)

        if len(sent_signals) > 1000:
            sent_signals.clear()

    except Exception as e:
        print(f"⚠️ Error procesando {symbol} en 3m: {e}", flush=True)

async def bucle_bot():
    send_telegram("⏰ *Bot FVG V3 Activo*\nLógica de documentación aplicada de forma estricta (TP +4% / SL -3%).")

    while True:
        now = datetime.now(timezone.utc)
        seconds_to_next_3m = 180 - ((now.minute % 3) * 60 + now.second)
        sleep_time = seconds_to_next_3m + 2

        if sleep_time < 5:
            sleep_time += 180

        await asyncio.sleep(sleep_time)
        print(f"[{datetime.now(timezone.utc).strftime('%H:%M:%S')}] Escaneando mercado (3m)...", flush=True)
        
        for symbol in SYMBOLS:
            run_fvg_v3_strategy(symbol, "3m")
            await asyncio.sleep(0.04)

async def handle_ping(request):
    return web.Response(text="Bot FVG V3 Estricto Activo")

async def main():
    app = web.Application()
    app.router.add_get("/", handle_ping)
    port = int(os.environ.get("PORT", 10000))
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    asyncio.create_task(bucle_bot())
    while True:
        await asyncio.sleep(3600)

if __name__ == "__main__":
    asyncio.run(main())
