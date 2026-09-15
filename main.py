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

TP1_PERCENT = 0.010  # 1% de ganancia desde el 50% FVG
SL_PERCENT = 0.050   # 5% de pérdida desde el 50% FVG

sent_signals = set()

SYMBOLS = list(set([
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
    "DENT/USDT", "KEY/USDT", "TWT/USDT", "COS/USDT", "CTXC/USDT", "HBAR/USDT", "MUBARAK/USDT"
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
        if not bars or len(bars) < 100:
            return

        df = pd.DataFrame(
            bars, columns=["time", "open", "high", "low", "close", "volume"]
        )
        # Excluimos la vela actual en formación (solo operamos velas cerradas)
        df = df.iloc[:-1].copy()

        # ==========================================
        # 1. CÁLCULO PRECISO DE INDICADORES (IGUAL A TRADINGVIEW)
        # ==========================================
        # Bollinger Bands (TV usa ddof=0 para StdDev poblacional)
        df["sma"] = df["close"].rolling(window=BB_LENGTH).mean()
        df["std"] = df["close"].rolling(window=BB_LENGTH).std(ddof=0) 
        df["upper_bb"] = df["sma"] + (BB_STD * df["std"])
        df["lower_bb"] = df["sma"] - (BB_STD * df["std"])

        # RSI (TV usa RMA/Wilder's Smoothing, no SMA simple)
        delta = df['close'].diff()
        gain = delta.where(delta > 0, 0.0)
        loss = -delta.where(delta < 0, 0.0)
        alpha = 1 / RSI_LENGTH
        df['avg_gain'] = gain.ewm(alpha=alpha, min_periods=RSI_LENGTH, adjust=False).mean()
        df['avg_loss'] = loss.ewm(alpha=alpha, min_periods=RSI_LENGTH, adjust=False).mean()
        rs = df['avg_gain'] / df['avg_loss']
        df['rsi'] = 100 - (100 / (1 + rs))

        # ==========================================
        # 2. MÁQUINA DE ESTADOS ESTRICTA
        # ==========================================
        # 0 = Buscando Señal | 1 = Esperando Barrido | 2 = Esperando FVG
        long_state = 0
        long_ref_level = 0.0
        
        short_state = 0
        short_ref_level = 0.0

        for i in range(2, len(df)):
            # --- EVALUACIÓN DE FVG (Solo importa si estamos en Estado 2) ---
            bullish_fvg = df['low'].iloc[i] > df['high'].iloc[i-2]
            bearish_fvg = df['high'].iloc[i] < df['low'].iloc[i-2]

            # LONG: Chequear si FVG completó la secuencia
            if long_state == 2 and bullish_fvg:
                # Si el FVG acaba de cerrarse en LA ÚLTIMA vela de la gráfica, ¡Disparamos!
                if i == len(df) - 1:
                    fvg_mid = (df['high'].iloc[i-2] + df['low'].iloc[i]) / 2.0
                    tp1 = fvg_mid * (1 + TP1_PERCENT) # +1%
                    sl = fvg_mid * (1 - SL_PERCENT)   # -5%
                    
                    seq_id = f"{symbol}_LONG_{df['time'].iloc[i]}"
                    if seq_id not in sent_signals:
                        clean_symbol = symbol.replace("/", "") + ".P"
                        msg = (
                            f"🟢 *LONG · Setup Completado (3m)*\n"
                            f"Par: `{clean_symbol}`\n"
                            f"📍 Entrada Límite (50% FVG): `{fvg_mid:.6f}`\n"
                            f"🎯 Take Profit (+1%): `{tp1:.6f}`\n"
                            f"🛑 Stop Loss (-5%): `{sl:.6f}`\n"
                            f"_Secuencia: Señal > Barrido > FVG_ ✅"
                        )
                        send_telegram(msg)
                        sent_signals.add(seq_id)
                # RESET: Haya alertado o sea histórico, el patrón terminó. A buscar otro.
                long_state = 0 

            # SHORT: Chequear si FVG completó la secuencia
            if short_state == 2 and bearish_fvg:
                if i == len(df) - 1:
                    fvg_mid = (df['low'].iloc[i-2] + df['high'].iloc[i]) / 2.0
                    tp1 = fvg_mid * (1 - TP1_PERCENT) # +1% hacia abajo
                    sl = fvg_mid * (1 + SL_PERCENT)   # -5% hacia arriba
                    
                    seq_id = f"{symbol}_SHORT_{df['time'].iloc[i]}"
                    if seq_id not in sent_signals:
                        clean_symbol = symbol.replace("/", "") + ".P"
                        msg = (
                            f"🔴 *SHORT · Setup Completado (3m)*\n"
                            f"Par: `{clean_symbol}`\n"
                            f"📍 Entrada Límite (50% FVG): `{fvg_mid:.6f}`\n"
                            f"🎯 Take Profit (+1%): `{tp1:.6f}`\n"
                            f"🛑 Stop Loss (-5%): `{sl:.6f}`\n"
                            f"_Secuencia: Señal > Barrido > FVG_ ✅"
                        )
                        send_telegram(msg)
                        sent_signals.add(seq_id)
                short_state = 0 


            # --- EVALUACIÓN DE BARRIDO CON CUERPO (Estado 1 -> Estado 2) ---
            # Si estamos esperando barrido LONG y el precio CIERRA por debajo del mínimo de la señal:
            if long_state == 1 and df['close'].iloc[i] < long_ref_level:
                long_state = 2
                
            # Si estamos esperando barrido SHORT y el precio CIERRA por encima del máximo de la señal:
            if short_state == 1 and df['close'].iloc[i] > short_ref_level:
                short_state = 2


            # --- DETECCIÓN DE NUEVA VELA SEÑAL (Actualiza a Estado 1) ---
            # RSI en zona + toque de BB. (Si esto pasa, se resetea y empieza nueva secuencia)
            if df['low'].iloc[i] <= df['lower_bb'].iloc[i] and df['rsi'].iloc[i] <= RSI_OVERSOLD:
                long_state = 1
                long_ref_level = df['low'].iloc[i]
                
            if df['high'].iloc[i] >= df['upper_bb'].iloc[i] and df['rsi'].iloc[i] >= RSI_OVERBOUGHT:
                short_state = 1
                short_ref_level = df['high'].iloc[i]

        # Limpiar caché de Telegram si crece demasiado
        if len(sent_signals) > 1000:
            sent_signals.clear()

    except Exception as e:
        pass # Silenciado para evitar spam en consola, descomentar print(e) si depuras

async def bucle_bot():
    send_telegram("⏰ *Bot Iniciado*\n- Lógica Anti-Spam Activada (No envía señales dobles).\n- TP 1% / SL 5%.\n- Barrido validado con cierre de cuerpo.")

    while True:
        now = datetime.now(timezone.utc)
        # Sincronización exacta de velas de 3 minutos
        seconds_to_next_3m = 180 - ((now.minute % 3) * 60 + now.second)
        sleep_time = seconds_to_next_3m + 2 # Margen de 2 segundos para asegurar cierre

        if sleep_time < 5:
            sleep_time += 180

        await asyncio.sleep(sleep_time)
        
        for symbol in SYMBOLS:
            run_fvg_v3_strategy(symbol, "3m")
            await asyncio.sleep(0.04) # Límite API Binance

async def handle_ping(request):
    return web.Response(text="Bot FVG Anti-Spam (3m) Activo")

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
