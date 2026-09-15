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
# PARÁMETROS CONFIGURADOS
# ==========================================
BB_LEN = 20
BB_MULT = 2.0
RSI_LEN = 14
RSI_OB = 70.0
RSI_OS = 30.0

ATR_LEN = 14
MIN_GAP_ATR = 0.40
MAX_BAND_ATR = 3.0
MAX_SWEEP_CANDLES = 96
MAX_WAIT_FVG = 960

sent_signals = set()

# LISTA COMPLETA DE MONEDAS (USDT-M)
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

def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try:
        requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown"}, timeout=10)
    except Exception as e:
        print(f"Error Telegram: {e}", flush=True)

def run_fvg_v3_strategy(symbol, timeframe):
    try:
        bars = exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=600)
        if not bars or len(bars) < 150: return
        df = pd.DataFrame(bars, columns=["time", "open", "high", "low", "close", "volume"])

        # 1. Indicadores Base
        df["sma"] = df["close"].rolling(window=BB_LEN).mean()
        df["std"] = df["close"].rolling(window=BB_LEN).std(ddof=0)
        df["upper_bb"] = df["sma"] + (BB_MULT * df["std"])
        df["lower_bb"] = df["sma"] - (BB_MULT * df["std"])

        delta = df['close'].diff()
        gain = delta.where(delta > 0, 0.0)
        loss = -delta.where(delta < 0, 0.0)
        alpha = 1 / RSI_LEN
        df['avg_gain'] = gain.ewm(alpha=alpha, min_periods=RSI_LEN, adjust=False).mean()
        df['avg_loss'] = loss.ewm(alpha=alpha, min_periods=RSI_LEN, adjust=False).mean()
        df['rsi'] = 100 - (100 / (1 + (df['avg_gain'] / df['avg_loss'])))

        df['prev_close'] = df['close'].shift(1)
        df['tr'] = df[['high', 'low', 'prev_close']].apply(
            lambda row: max(row['high'] - row['low'], abs(row['high'] - row['prev_close']), abs(row['low'] - row['prev_close'])), axis=1
        )
        df['atr'] = df['tr'].rolling(window=ATR_LEN).mean()

        # 2. Máquina de Estados sincronizada a la vela de cierre exacta
        state = "idle"
        direction = None
        sigPrice = 0.0
        sigHigh = 0.0
        sigLow = 0.0
        sigBar = 0
        extremeFavor = 0.0
        sweepBar = 0
        entryPrice = 0.0

        last_closed_idx = len(df) - 2

        for i in range(30, len(df) - 1):
            close_i = df['close'].iloc[i]
            lower_i = df['lower_bb'].iloc[i]
            upper_i = df['upper_bb'].iloc[i]
            rsi_i = df['rsi'].iloc[i]

            if state == "idle":
                stretchLong = close_i < lower_i
                stretchShort = close_i > upper_i
                signalLong = stretchLong and rsi_i < RSI_OS
                signalShort = stretchShort and rsi_i > RSI_OB

                if signalLong or signalShort:
                    direction = "long" if signalLong else "short"
                    sigBar = i
                    sigHigh = df['high'].iloc[i]
                    sigLow = df['low'].iloc[i]
                    sigPrice = close_i
                    extremeFavor = sigHigh if direction == "long" else sigLow
                    state = "sweep"

            if state == "sweep":
                if i - sigBar > MAX_SWEEP_CANDLES:
                    state = "idle"
                else:
                    sweepCond = (close_i < sigLow) if direction == "long" else (close_i > sigHigh)
                    if sweepCond:
                        sweepBar = i
                        state = "fvg"

            if state == "fvg":
                high_i = df['high'].iloc[i]
                low_i = df['low'].iloc[i]
                atr_i = df['atr'].iloc[i]

                if direction == "long":
                    extremeFavor = max(extremeFavor, high_i)
                    favorATR = (extremeFavor - sigPrice) / atr_i if atr_i > 0 else 0
                else:
                    extremeFavor = min(extremeFavor, low_i)
                    favorATR = (sigPrice - extremeFavor) / atr_i if atr_i > 0 else 0

                if favorATR > MAX_BAND_ATR:
                    state = "idle"
                elif i - sweepBar > MAX_SWEEP_CANDLES:
                    state = "idle"
                else:
                    bullFVG = (direction == "long") and (low_i > df['high'].iloc[i-2])
                    bearFVG = (direction == "short") and (high_i < df['low'].iloc[i-2])

                    if bullFVG or bearFVG:
                        gTop = low_i if direction == "long" else df['low'].iloc[i-2]
                        gBot = df['high'].iloc[i-2] if direction == "long" else high_i
                        gSize = gTop - gBot
                        gAtr = gSize / atr_i if atr_i > 0 else 0
                        gMid = (gTop + gBot) / 2.0
                        midDistATR = abs(gMid - sigPrice) / atr_i if atr_i > 0 else 0

                        if gAtr >= MIN_GAP_ATR and midDistATR <= MAX_BAND_ATR:
                            entryPrice = gMid
                            state = "wait_fill"

                            # Envío exacto en la siguiente vela tras formarse el FVG en la última vela cerrada
                            if i == last_closed_idx:
                                time_val = df['time'].iloc[i]
                                seq_id = f"{symbol}_{direction}_{time_val}"
                                if seq_id not in sent_signals:
                                    candle_range_pct = ((high_i - low_i) / low_i) * 100
                                    msg = (
                                        f"📌 *Estrategia FVG V3 (3m)*\n"
                                        f"Par: `{symbol.replace('/', '')}.P`\n"
                                        f"Dirección: *{direction.upper()}*\n"
                                        f"📊 Rango Vela: `{candle_range_pct:.2f}%`\n"
                                        f"📍 Entrada Límite (50% FVG): `{entryPrice:.6f}`\n"
                                        f"✅ Alerta precisa en la siguiente vela"
                                    )
                                    send_telegram(msg)
                                    sent_signals.add(seq_id)

            elif state == "wait_fill":
                if i - sweepBar > MAX_WAIT_FVG:
                    state = "idle"
                else:
                    if (df['low'].iloc[i] <= entryPrice) if direction == "long" else (df['high'].iloc[i] >= entryPrice):
                        state = "filled"

            elif state == "filled":
                if (df['high'].iloc[i] >= entryPrice * 1.04) if direction == "long" else (df['low'].iloc[i] <= entryPrice * 0.96):
                    state = "idle"
                elif (df['low'].iloc[i] <= entryPrice * 0.97) if direction == "long" else (df['high'].iloc[i] >= entryPrice * 1.03):
                    state = "idle"

        if len(sent_signals) > 2000: sent_signals.clear()
    except Exception:
        pass

async def bucle_bot():
    send_telegram("🚀 *Bot FVG V3 Sincronizado*\n✅ Sintonizado a la perfección: Alerta exactamente en la siguiente vela del FVG.")
    while True:
        now = datetime.now(timezone.utc)
        sleep_time = (180 - ((now.minute % 3) * 60 + now.second)) + 2
        if sleep_time < 5: sleep_time += 180
        await asyncio.sleep(sleep_time)
        for symbol in SYMBOLS:
            run_fvg_v3_strategy(symbol, "3m")
            await asyncio.sleep(0.04)

async def handle_ping(request): return web.Response(text="Bot FVG V3 Activo")

async def main():
    app = web.Application()
    app.router.add_get("/", handle_ping)
    runner = web.AppRunner(app)
    await runner.setup()
    await web.TCPSite(runner, "0.0.0.0", int(os.environ.get("PORT", 10000))).start()
    asyncio.create_task(bucle_bot())
    while True: await asyncio.sleep(3600)

if __name__ == "__main__": asyncio.run(main())
