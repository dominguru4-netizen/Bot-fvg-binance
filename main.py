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

TP1_PERCENT = 0.010  # 1%
SL_PERCENT = 0.050   # 5%

sent_signals = set()

SYMBOLS = list(set([
    "H/USDT", "BTC/USDT", "ETH/USDT", "SOL/USDT", "BNB/USDT", "XRP/USDT", "ADA/USDT", 
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

exchange = ccxt.binance(
    {"enableRateLimit": True, "options": {"defaultType": "swap"}}
)

def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown"}
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"Error Telegram: {e}", flush=True)

def run_fvg_v3_strategy(symbol, timeframe):
    try:
        # 300 velas de historial (~15 horas) sin límites artificiales
        bars = exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=300)
        if not bars or len(bars) < 100:
            return

        df = pd.DataFrame(bars, columns=["time", "open", "high", "low", "close", "volume"])
        df = df.iloc[:-1].copy() # Solo velas cerradas

        # --- INDICADORES (Misma fórmula matemática de TradingView) ---
        df["sma"] = df["close"].rolling(window=BB_LENGTH).mean()
        df["std"] = df["close"].rolling(window=BB_LENGTH).std(ddof=0)
        df["upper_bb"] = df["sma"] + (BB_STD * df["std"])
        df["lower_bb"] = df["sma"] - (BB_STD * df["std"])

        delta = df['close'].diff()
        gain = delta.where(delta > 0, 0.0)
        loss = -delta.where(delta < 0, 0.0)
        alpha = 1 / RSI_LENGTH
        df['avg_gain'] = gain.ewm(alpha=alpha, min_periods=RSI_LENGTH, adjust=False).mean()
        df['avg_loss'] = loss.ewm(alpha=alpha, min_periods=RSI_LENGTH, adjust=False).mean()
        df['rsi'] = 100 - (100 / (1 + (df['avg_gain'] / df['avg_loss'])))

        # --- MÁQUINA DE ESTADOS IDÉNTICA A TRADINGVIEW ---
        long_state = 0
        long_ref_low = 0.0

        short_state = 0
        short_ref_high = 0.0

        for i in range(2, len(df)):
            c_open = df['open'].iloc[i]
            c_high = df['high'].iloc[i]
            c_low = df['low'].iloc[i]
            c_close = df['close'].iloc[i]
            c_rsi = df['rsi'].iloc[i]
            c_lower_bb = df['lower_bb'].iloc[i]
            c_upper_bb = df['upper_bb'].iloc[i]

            # ----------------------------------------------------
            # SECUENCIA LONG
            # ----------------------------------------------------
            # 1. Señal sobreventa + toque de banda inferior
            if c_low <= c_lower_bb and c_rsi <= RSI_OVERSOLD:
                long_state = 1
                long_ref_low = c_low

            # 2. Barrido con cuerpo (cierre < mínimo de la vela señal)
            elif long_state == 1:
                if c_close < long_ref_low:
                    long_state = 2  # Barrido confirmado

            # 3. Formación de FVG Alcista (espera ilimitada)
            elif long_state == 2:
                prev1_open = df['open'].iloc[i-1]
                prev1_close = df['close'].iloc[i-1]
                prev2_high = df['high'].iloc[i-2]

                # FVG Alcista Real: Vela intermedia VERDE + Hueco de precio
                is_bullish_fvg = (prev1_close > prev1_open) and (c_low > prev2_high)

                if is_bullish_fvg:
                    if i >= len(df) - 2:
                        fvg_mid = (prev2_high + c_low) / 2.0
                        seq_id = f"{symbol}_LONG_{df['time'].iloc[i]}"

                        if seq_id not in sent_signals:
                            tp1 = fvg_mid * (1 + TP1_PERCENT)
                            sl = fvg_mid * (1 - SL_PERCENT)
                            clean_sym = symbol.replace("/", "") + ".P"
                            msg = (
                                f"🟢 *LONG · Setup V3 (3m)*\n"
                                f"Par: `{clean_sym}`\n"
                                f"📍 Entrada Límite (50% FVG): `{fvg_mid:.6f}`\n"
                                f"🎯 Take Profit (+1%): `{tp1:.6f}`\n"
                                f"🛑 Stop Loss (-5%): `{sl:.6f}`\n"
                                f"✅ Secuencia: Señal > Barrido > FVG"
                            )
                            send_telegram(msg)
                            sent_signals.add(seq_id)

                    long_state = 0  # Se completa la secuencia y resetea

            # ----------------------------------------------------
            # SECUENCIA SHORT
            # ----------------------------------------------------
            # 1. Señal sobrecompra + toque de banda superior
            if c_high >= c_upper_bb and c_rsi >= RSI_OVERBOUGHT:
                short_state = 1
                short_ref_high = c_high

            # 2. Barrido con cuerpo (cierre > máximo de la vela señal)
            elif short_state == 1:
                if c_close > short_ref_high:
                    short_state = 2  # Barrido confirmado

            # 3. Formación de FVG Bajista (espera ilimitada)
            elif short_state == 2:
                prev1_open = df['open'].iloc[i-1]
                prev1_close = df['close'].iloc[i-1]
                prev2_low = df['low'].iloc[i-2]

                # FVG Bajista Real: Vela intermedia ROJA + Hueco de precio
                is_bearish_fvg = (prev1_close < prev1_open) and (c_high < prev2_low)

                if is_bearish_fvg:
                    if i >= len(df) - 2:
                        fvg_mid = (prev2_low + c_high) / 2.0
                        seq_id = f"{symbol}_SHORT_{df['time'].iloc[i]}"

                        if seq_id not in sent_signals:
                            tp1 = fvg_mid * (1 - TP1_PERCENT)
                            sl = fvg_mid * (1 + SL_PERCENT)
                            clean_sym = symbol.replace("/", "") + ".P"
                            msg = (
                                f"🔴 *SHORT · Setup V3 (3m)*\n"
                                f"Par: `{clean_sym}`\n"
                                f"📍 Entrada Límite (50% FVG): `{fvg_mid:.6f}`\n"
                                f"🎯 Take Profit (+1%): `{tp1:.6f}`\n"
                                f"🛑 Stop Loss (-5%): `{sl:.6f}`\n"
                                f"✅ Secuencia: Señal > Barrido > FVG"
                            )
                            send_telegram(msg)
                            sent_signals.add(seq_id)

                    short_state = 0  # Se completa la secuencia y resetea

        if len(sent_signals) > 2000:
            sent_signals.clear()

    except Exception:
        pass

async def bucle_bot():
    send_telegram("⏰ *Bot Calibrado 100% TradingView*\n- Sin límites de tiempo.\n- Validación estricta de color en FVG.\n- Sincronización exacta con 3m.")

    while True:
        now = datetime.now(timezone.utc)
        seconds_to_next_3m = 180 - ((now.minute % 3) * 60 + now.second)
        sleep_time = seconds_to_next_3m + 2

        if sleep_time < 5:
            sleep_time += 180

        await asyncio.sleep(sleep_time)
        
        for symbol in SYMBOLS:
            run_fvg_v3_strategy(symbol, "3m")
            await asyncio.sleep(0.04)

async def handle_ping(request):
    return web.Response(text="Bot FVG TradingView Match Activo")

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
