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
# PARÁMETROS GLOBALES
# ==========================================
BB_LENGTH = 20
BB_STD = 2.0
RSI_LENGTH = 14
RSI_OVERBOUGHT = 65
RSI_OVERSOLD = 35

TP1_PERCENT = 0.010
SL_PERCENT = 0.050

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

exchange = ccxt.binance({"enableRateLimit": True, "options": {"defaultType": "swap"}})

def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try:
        requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown"}, timeout=10)
    except Exception as e:
        print(f"Error Telegram: {e}", flush=True)

def check_bullish_divergence(df, current_idx, lookback=15):
    if current_idx < lookback: return False
    curr_low = df['low'].iloc[current_idx]
    curr_rsi = df['rsi'].iloc[current_idx]
    for j in range(current_idx - 3, current_idx - lookback, -1):
        if j < 0: break
        if curr_low < df['low'].iloc[j] and curr_rsi > df['rsi'].iloc[j]:
            return True
    return False

def check_bearish_divergence(df, current_idx, lookback=15):
    if current_idx < lookback: return False
    curr_high = df['high'].iloc[current_idx]
    curr_rsi = df['rsi'].iloc[current_idx]
    for j in range(current_idx - 3, current_idx - lookback, -1):
        if j < 0: break
        if curr_high > df['high'].iloc[j] and curr_rsi < df['rsi'].iloc[j]:
            return True
    return False

def run_fvg_v3_strategy(symbol, timeframe):
    try:
        bars = exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=300)
        if not bars or len(bars) < 100: return
        df = pd.DataFrame(bars, columns=["time", "open", "high", "low", "close", "volume"]).iloc[:-1].copy()

        # --- BANDAS DE BOLLINGER ---
        df["sma"] = df["close"].rolling(window=BB_LENGTH).mean()
        df["std"] = df["close"].rolling(window=BB_LENGTH).std(ddof=0)
        df["upper_bb"] = df["sma"] + (BB_STD * df["std"])
        df["lower_bb"] = df["sma"] - (BB_STD * df["std"])

        # --- RSI ---
        delta = df['close'].diff()
        gain = delta.where(delta > 0, 0.0)
        loss = -delta.where(delta < 0, 0.0)
        alpha = 1 / RSI_LENGTH
        df['avg_gain'] = gain.ewm(alpha=alpha, min_periods=RSI_LENGTH, adjust=False).mean()
        df['avg_loss'] = loss.ewm(alpha=alpha, min_periods=RSI_LENGTH, adjust=False).mean()
        df['rsi'] = 100 - (100 / (1 + (df['avg_gain'] / df['avg_loss'])))

        # --- ATR (Vela Grande) ---
        df['prev_close'] = df['close'].shift(1)
        df['tr'] = df[['high', 'low', 'prev_close']].apply(
            lambda row: max(row['high'] - row['low'], abs(row['high'] - row['prev_close']), abs(row['low'] - row['prev_close'])), axis=1
        )
        df['atr'] = df['tr'].rolling(window=14).mean()

        long_state, long_ref_low, long_counter = 0, 0.0, 0
        short_state, short_ref_high, short_counter = 0, 0.0, 0

        for i in range(20, len(df)):
            c_open, c_high, c_low, c_close = df['open'].iloc[i], df['high'].iloc[i], df['low'].iloc[i], df['close'].iloc[i]
            c_rsi, c_lower_bb, c_upper_bb = df['rsi'].iloc[i], df['lower_bb'].iloc[i], df['upper_bb'].iloc[i]
            c_atr = df['atr'].iloc[i]

            vela_size = c_high - c_low
            is_vela_grande = vela_size > c_atr

            # =====================================================================
            # 🔥 KILL SWITCH & EXPIRACIÓN DE ESTADOS (Margen ampliado a 12 velas)
            # =====================================================================
            if long_state > 0:
                long_counter += 1
                if c_high >= c_upper_bb or c_rsi >= RSI_OVERBOUGHT or long_counter > 12:
                    long_state, long_counter = 0, 0

            if short_state > 0:
                short_counter += 1
                if c_low <= c_lower_bb or c_rsi <= RSI_OVERSOLD or short_counter > 12:
                    short_state, short_counter = 0, 0

            # --- SECUENCIA LONG ---
            has_bull_div = check_bullish_divergence(df, i)
            if c_low < c_lower_bb and c_rsi <= RSI_OVERSOLD and is_vela_grande and has_bull_div:
                long_state, long_ref_low, long_counter = 1, c_low, 0
                
            elif long_state == 1 and c_close < long_ref_low:
                long_state = 2  # Barrido con cuerpo confirmado
                
            elif long_state == 2:
                prev1_open, prev1_close, prev2_high = df['open'].iloc[i-1], df['close'].iloc[i-1], df['high'].iloc[i-2]
                if (prev1_close > prev1_open) and (c_low > prev2_high): # FVG Alcista
                    if i >= len(df) - 2:
                        fvg_mid = (prev2_high + c_low) / 2.0
                        seq_id = f"{symbol}_LONG_{df['time'].iloc[i]}"
                        if seq_id not in sent_signals:
                            send_telegram(f"🟢 *LONG · Setup V3 (3m)*\nPar: `{symbol.replace('/', '')}.P`\n📍 Entrada Límite (50% FVG): `{fvg_mid:.6f}`\n🎯 TP1 (+1%): `{fvg_mid * (1 + TP1_PERCENT):.6f}`\n🛑 SL (-5%): `{fvg_mid * (1 - SL_PERCENT):.6f}`\n✅ Filtro Estricto: Divergencia + Rotura + Barrido + FVG")
                            sent_signals.add(seq_id)
                    long_state, long_counter = 0, 0

            # --- SECUENCIA SHORT ---
            has_bear_div = check_bearish_divergence(df, i)
            if c_high > c_upper_bb and c_rsi >= RSI_OVERBOUGHT and is_vela_grande and has_bear_div:
                short_state, short_ref_high, short_counter = 1, c_high, 0
                
            elif short_state == 1 and c_close > short_ref_high:
                short_state = 2  # Barrido con cuerpo confirmado
                
            elif short_state == 2:
                prev1_open, prev1_close, prev2_low = df['open'].iloc[i-1], df['close'].iloc[i-1], df['low'].iloc[i-2]
                if (prev1_close < prev1_open) and (c_high < prev2_low): # FVG Bajista
                    if i >= len(df) - 2:
                        fvg_mid = (prev2_low + c_high) / 2.0
                        seq_id = f"{symbol}_SHORT_{df['time'].iloc[i]}"
                        if seq_id not in sent_signals:
                            send_telegram(f"🔴 *SHORT · Setup V3 (3m)*\nPar: `{symbol.replace('/', '')}.P`\n📍 Entrada Límite (50% FVG): `{fvg_mid:.6f}`\n🎯 TP1 (+1%): `{fvg_mid * (1 - TP1_PERCENT):.6f}`\n🛑 SL (-5%): `{fvg_mid * (1 + SL_PERCENT):.6f}`\n✅ Filtro Estricto: Divergencia + Rotura + Barrido + FVG")
                            sent_signals.add(seq_id)
                    short_state, long_counter = 0, 0

        if len(sent_signals) > 2000: sent_signals.clear()
    except Exception:
        pass

async def bucle_bot():
    send_telegram("⏰ *Bot Actualizado (Ventana de 12 velas)*\n✅ Margen ampliado para capturar barridos que tardan un poco más en completarse.\n✅ Filtros estrictos activos.")
    while True:
        now = datetime.now(timezone.utc)
        sleep_time = (180 - ((now.minute % 3) * 60 + now.second)) + 2
        if sleep_time < 5: sleep_time += 180
        await asyncio.sleep(sleep_time)
        for symbol in SYMBOLS:
            run_fvg_v3_strategy(symbol, "3m")
            await asyncio.sleep(0.04)

async def handle_ping(request): return web.Response(text="Bot Activo con Margen Ampliado")

async def main():
    app = web.Application()
    app.router.add_get("/", handle_ping)
    runner = web.AppRunner(app)
    await runner.setup()
    await web.TCPSite(runner, "0.0.0.0", int(os.environ.get("PORT", 10000))).start()
    asyncio.create_task(bucle_bot())
    while True: await asyncio.sleep(3600)

if __name__ == "__main__": asyncio.run(main())
