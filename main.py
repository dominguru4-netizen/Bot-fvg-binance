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
# PARÁMETROS OFICIALES FVG V3
# ==========================================
BB_LENGTH = 20
BB_STD = 2.0
RSI_LENGTH = 14
RSI_OVERSOLD = 35
RSI_OVERBOUGHT = 65

TP_PERCENT = 0.04  # +4%
SL_PERCENT = 0.03  # -3%
GAP_ATR_MIN = 0.40 # gap_atr >= 0.40
MAX_SWEEP_CANDLES = 480 # 24 horas en velas de 3m

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
        bars = exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=350)
        if not bars or len(bars) < 120: return
        df = pd.DataFrame(bars, columns=["time", "open", "high", "low", "close", "volume"]).iloc[:-1].copy()

        # Indicadores base
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

        df['prev_close'] = df['close'].shift(1)
        df['tr'] = df[['high', 'low', 'prev_close']].apply(
            lambda row: max(row['high'] - row['low'], abs(row['high'] - row['prev_close']), abs(row['low'] - row['prev_close'])), axis=1
        )
        df['atr'] = df['tr'].rolling(window=14).mean()

        # Recorremos buscando señales BOT-S confirmadas
        for i in range(30, len(df) - 3):
            prev_open, prev_high, prev_low, prev_close = df['open'].iloc[i-1], df['high'].iloc[i-1], df['low'].iloc[i-1], df['close'].iloc[i-1]
            prev_rsi = df['rsi'].iloc[i-1]
            prev_lower = df['lower_bb'].iloc[i-1]
            prev_upper = df['upper_bb'].iloc[i-1]

            c_open, c_high, c_low, c_close = df['open'].iloc[i], df['high'].iloc[i], df['low'].iloc[i], df['close'].iloc[i]

            # LONG Signal Base BOT-S
            is_bot_s_long = (prev_low < prev_lower) and (prev_rsi <= RSI_OVERSOLD) and (c_close > c_open)
            # SHORT Signal Base BOT-S
            is_bot_s_short = (prev_high > prev_upper) and (prev_rsi >= RSI_OVERBOUGHT) and (c_close < c_open)

            if not is_bot_s_long and not is_bot_s_short:
                continue

            direction = "LONG" if is_bot_s_long else "SHORT"
            sig_price = c_close
            extreme_val = prev_low if direction == "LONG" else prev_high

            # Barrido de liquidez
            swept = False
            sweep_idx = -1
            
            for j in range(i + 1, min(i + 1 + MAX_SWEEP_CANDLES, len(df))):
                j_close = df['close'].iloc[j]
                curr_atr = df['atr'].iloc[j]
                
                # Cancelación si el precio rebasa 3 ATR a favor antes de formar el FVG
                if direction == "LONG" and (df['high'].iloc[j] - sig_price) > (3 * curr_atr):
                    break
                if direction == "SHORT" and (sig_price - df['low'].iloc[j]) > (3 * curr_atr):
                    break

                # Al menos 1 vela CIERRA más allá del extremo de la señal
                if direction == "LONG" and j_close < extreme_val:
                    swept = True
                    sweep_idx = j
                    break
                elif direction == "SHORT" and j_close > extreme_val:
                    swept = True
                    sweep_idx = j
                    break

            if not swept:
                continue

            # Buscar primer FVG a favor con gap_atr >= 0.40
            fvg_found = False
            fvg_mid = 0.0

            for k in range(sweep_idx, min(sweep_idx + 10, len(df) - 1)):
                k_atr = df['atr'].iloc[k]
                if direction == "LONG":
                    if (df['low'].iloc[k] > df['high'].iloc[k-2]) and (df['close'].iloc[k-1] > df['open'].iloc[k-1]):
                        gap_size = df['low'].iloc[k] - df['high'].iloc[k-2]
                        if (gap_size / k_atr) >= GAP_ATR_MIN:
                            fvg_mid = (df['high'].iloc[k-2] + df['low'].iloc[k]) / 2.0
                            if abs(fvg_mid - sig_price) <= (3 * k_atr):
                                fvg_found = True
                                break
                else:
                    if (df['high'].iloc[k] < df['low'].iloc[k-2]) and (df['close'].iloc[k-1] < df['open'].iloc[k-1]):
                        gap_size = df['low'].iloc[k-2] - df['high'].iloc[k]
                        if (gap_size / k_atr) >= GAP_ATR_MIN:
                            fvg_mid = (df['low'].iloc[k-2] + df['high'].iloc[k]) / 2.0
                            if abs(fvg_mid - sig_price) <= (3 * k_atr):
                                fvg_found = True
                                break

            if fvg_found:
                # Quitamos la restricción restrictiva de las últimas 2 velas para que cante 
                # la señal exactamente en la vela 'k' donde se forma el FVG (Línea Amarilla)
                seq_id = f"{symbol}_{direction}_{df['time'].iloc[k]}"
                if seq_id not in sent_signals:
                    tp_val = fvg_mid * (1 + TP_PERCENT) if direction == "LONG" else fvg_mid * (1 - TP_PERCENT)
                    sl_val = fvg_mid * (1 - SL_PERCENT) if direction == "LONG" else fvg_mid * (1 + SL_PERCENT)
                    
                    msg = (
                        f"📌 *Estrategia FVG V3 (3m)*\n"
                        f"Par: `{symbol.replace('/', '')}.P`\n"
                        f"Dirección: *{direction}*\n"
                        f"📍 Entrada Límite (50% FVG): `{fvg_mid:.6f}`\n"
                        f"🎯 TP (+4%): `{tp_val:.6f}`\n"
                        f"🛑 SL (-3%): `{sl_val:.6f}`\n"
                        f"✅ Sincronizado en la vela exacta del FVG"
                    )
                    send_telegram(msg)
                    sent_signals.add(seq_id)

        if len(sent_signals) > 2000: sent_signals.clear()
    except Exception:
        pass

async def bucle_bot():
    send_telegram("🚀 *Bot FVG V3 Actualizado*\n✅ Sincronización exacta en la vela del FVG (Línea Amarilla).")
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
