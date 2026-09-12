import time
import os
import ccxt
import pandas as pd
import requests
from aiohttp import web
import asyncio

# ==========================================
# CREDENCIALES TELEGRAM
# ==========================================
TELEGRAM_TOKEN = "8638598049:AAEcQ2kjt9qM_PywnFTZs-2mY-3O8ahW-B0"
TELEGRAM_CHAT_ID = "2118999160"

# ==========================================
# PARÁMETROS EXACTOS DE TRADINGVIEW (FVG V3)
# ==========================================
TIMEFRAME = '5m'          
LIMIT_SWEEP = 96          # Máx. velas para el barrido
SL_PERCENT = 0.050        # Stop Loss 5%
TP1_PERCENT = 0.007       # Take Profit 0.7%
MAX_VALIDEZ_ATR = 10.0    # Banda máx. de validez (x ATR)

# LISTA DE PARES DE FUTUROS (Sufijo .P)
SYMBOLS = [
    'BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'BNB/USDT', 'XRP/USDT', 'ADA/USDT', 'AVAX/USDT', 'DOGE/USDT', 'DOT/USDT', 'LINK/USDT',
    'NEAR/USDT', 'SUI/USDT', 'PEPE/USDT', 'SHIB/USDT', 'LTC/USDT', 'UNI/USDT', 'APT/USDT', 'BCH/USDT', 'ICP/USDT', 'FET/USDT',
    'RENDER/USDT', 'ETC/USDT', 'FIL/USDT', 'XMR/USDT', 'TIA/USDT', 'ATOM/USDT', 'STX/USDT', 'INJ/USDT', 'WIF/USDT', 'OP/USDT',
    'ARB/USDT', 'THETA/USDT', 'GRT/USDT', 'RUNE/USDT', 'FTM/USDT', 'SEI/USDT', 'FLOKI/USDT', 'BONK/USDT', 'JUP/USDT', 'AAVE/USDT',
    'MKR/USDT', 'ORDI/USDT', 'EGLD/USDT', 'SAND/USDT', 'EOS/USDT', 'MANA/USDT', 'XTZ/USDT', 'ALGO/USDT', 'FLOW/USDT', 'AXS/USDT',
    'GALA/USDT', 'SNX/USDT', 'NEO/USDT', 'KAVA/USDT', 'ROSE/USDT', 'CHZ/USDT', 'IOTA/USDT', 'MINA/USDT', 'COMP/USDT', 'CRV/USDT',
    'ZEC/USDT', 'KSM/USDT', 'DASH/USDT', '1INCH/USDT', 'ENJ/USDT', 'BAT/USDT', 'WOO/USDT', 'GMT/USDT', 'LRC/USDT', 'DYDX/USDT',
    'CFX/USDT', 'CKB/USDT', 'AR/USDT', 'BLUR/USDT', 'ARKM/USDT', 'STRK/USDT', 'ENA/USDT', 'TNSR/USDT', 'W/USDT', 'OM/USDT',
    'BOME/USDT', 'NOT/USDT', 'IO/USDT', 'ZK/USDT', 'ZRO/USDT', 'TURBO/USDT', 'LISTA/USDT', 'DOGS/USDT', 'CATI/USDT', 'HMSTR/USDT',
    'EIGEN/USDT', 'NEIRO/USDT', 'MEW/USDT', 'MEME/USDT', 'BEAM/USDT', 'RONIN/USDT', 'PIXEL/USDT', 'ALT/USDT', 'MANTA/USDT', 'XAI/USDT',
    'ACE/USDT', 'NFP/USDT', 'AI/USDT', 'PORTAL/USDT', 'AEVO/USDT', 'ETHFI/USDT', 'SAGA/USDT', 'OMNI/USDT', 'REZ/USDT', 'BB/USDT',
    'BANANA/USDT', 'SYN/USDT', 'PENDLE/USDT', 'CELO/USDT', 'ONE/USDT', 'HOT/USDT', 'ZIL/USDT', 'RVN/USDT', 'ANKR/USDT', 'AUDIO/USDT',
    'LDO/USDT', 'STORJ/USDT', 'SKL/USDT', 'ICX/USDT', 'ZRX/USDT', 'ONT/USDT', 'WAXP/USDT', 'SPELL/USDT', 'SLP/USDT', 'ALPHA/USDT',
    'COTI/USDT', 'ZEN/USDT', 'STRAX/USDT', 'SXP/USDT', 'C98/USDT', 'CHR/USDT', 'OXT/USDT', 'NMR/USDT', 'TRB/USDT', 'BAND/USDT',
    'RLC/USDT', 'API3/USDT', 'TRU/USDT', 'BADGER/USDT', 'POND/USDT', 'PERP/USDT', 'ALICE/USDT', 'SUPER/USDT', 'UNFI/USDT', 'LIT/USDT',
    'SFP/USDT', 'DODO/USDT', 'BEL/USDT', 'CTSI/USDT', 'DAR/USDT', 'MOVR/USDT', 'SYS/USDT', 'PEOPLE/USDT', 'ACH/USDT', 'AGLD/USDT',
    'GLMR/USDT', 'ASTR/USDT', 'BSW/USDT', 'CVX/USDT', 'FIS/USDT', 'STPT/USDT', 'RAD/USDT', 'T/USDT', 'PROS/USDT', 'VTHO/USDT',
    'WRX/USDT', 'MBL/USDT', 'DENT/USDT', 'KEY/USDT', 'TWT/USDT', 'COS/USDT', 'CTXC/USDT'
]

exchange = ccxt.binance({
    'enableRateLimit': True,
    'options': {'defaultType': 'swap'}
})

def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown"}
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception:
        pass

def run_strategy_for_symbol(symbol):
    try:
        bars = exchange.fetch_ohlcv(symbol, timeframe=TIMEFRAME, limit=150)
        if not bars or len(bars) < 120:
            return
            
        df = pd.DataFrame(bars, columns=['time', 'open', 'high', 'low', 'close', 'volume'])
        
        # --- INDICADORES ---
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))

        sma = df['close'].rolling(window=20).mean()
        std = df['close'].rolling(window=20).std()
        df['bb_lower'] = sma - (std * 2.0)
        df['bb_upper'] = sma + (std * 2.0)

        df['ema_27'] = df['close'].rolling(window=27).mean()
        df['vol_sma'] = df['volume'].rolling(window=20).mean()

        high_low = df['high'] - df['low']
        high_close = (df['high'] - df['close'].shift()).abs()
        low_close = (df['low'] - df['close'].shift()).abs()
        true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        df['atr'] = true_range.rolling(window=14).mean()

        # Variables actuales
        c_close = df['close'].iloc[-2]
        c_high = df['high'].iloc[-2]
        c_low = df['low'].iloc[-2]
        c_vol = df['volume'].iloc[-2]
        ema_val = df['ema_27'].iloc[-2]
        atr_val = df['atr'].iloc[-2]
        
        # --- 1. FVG REVERSIÓN ---
        v1_high = df['high'].iloc[-4]
        v1_low = df['low'].iloc[-4]
        v3_low = df['low'].iloc[-2]
        v3_high = df['high'].iloc[-2]

        fvg_bullish = v3_low > v1_high
        fvg_bearish = v3_high < v1_low
        fvg_gap = v3_low - v1_high if fvg_bullish else (v1_low - v3_high if fvg_bearish else 0)
        
        # Validación con el límite de validez (x ATR en 10) y mínimo > 0
        fvg_valido = (fvg_gap > 0) and (fvg_gap <= atr_val * MAX_VALIDEZ_ATR)

        # Barrido de 96 velas
        min_previo = df['low'].iloc[-(LIMIT_SWEEP+2):-2].min()
        max_previo = df['high'].iloc[-(LIMIT_SWEEP+2):-2].max()
        swept_low = c_low < min_previo
        swept_high = c_high > max_previo

        oversold = (df['rsi'].iloc[-2] < 35) or (c_low <= df['bb_lower'].iloc[-2])
        overbought = (df['rsi'].iloc[-2] > 65) or (c_high >= df['bb_upper'].iloc[-2])

        # --- 2. FVG TENDENCIA / CONTINUACIÓN ---
        v1_high_p = df['high'].iloc[-5]
        v1_low_p = df['low'].iloc[-5]
        v3_low_p = df['low'].iloc[-3]
        v3_high_p = df['high'].iloc[-3]

        fvg_bullish_p = v3_low_p > v1_high_p
        fvg_bearish_p = v3_high_p < v1_low_p
        fvg_gap_p = v3_low_p - v1_high_p if fvg_bullish_p else (v1_low_p - v3_high_p if fvg_bearish_p else 0)
        fvg_valido_p = (fvg_gap_p > 0) and (fvg_gap_p <= atr_val * MAX_VALIDEZ_ATR)

        rebote_bullish = fvg_bullish_p and fvg_valido_p and (c_low <= v3_low_p) and (c_close > v1_high_p)
        rebote_bearish = fvg_bearish_p and fvg_valido_p and (c_high >= v3_high_p) and (c_close < v1_low_p)

        tendencia_alcista = c_close > ema_val
        tendencia_bajista = c_close < ema_val
        volumen_alto = c_vol > (df['vol_sma'].iloc[-2] * 1.2)

        clean_symbol = symbol.replace('/', '') + '.P'

        # --- DISPAROS DE REVERSIÓN ---
        if fvg_bullish and fvg_valido and swept_low and oversold:
            sl = v1_high * (1 - SL_PERCENT)
            tp1 = v1_high * (1 + TP1_PERCENT)
            msg = (
                f"🟢 *LONG · FVG (Reversión)*\n"
                f"Par: `{clean_symbol}`\n"
                f"Entrada FVG: `{v1_high:.4f}`\n"
                f"Stop Loss: `{sl:.4f}` | TP: `{tp1:.4f}`"
            )
            send_telegram(msg)
            
        if fvg_bearish and fvg_valido and swept_high and overbought:
            sl = v1_low * (1 + SL_PERCENT)
            tp1 = v1_low * (1 - TP1_PERCENT)
            msg = (
                f"🔴 *SHORT · FVG (Reversión)*\n"
                f"Par: `{clean_symbol}`\n"
                f"Entrada FVG: `{v3_high:.4f}`\n"
                f"Stop Loss: `{sl:.4f}` | TP: `{tp1:.4f}`"
            )
            send_telegram(msg)

        # --- DISPAROS DE TENDENCIA / CONTINUACIÓN ---
        if rebote_bullish and tendencia_alcista and volumen_alto:
            sl = v1_high_p * (1 - SL_PERCENT)
            tp1 = c_close * (1 + TP1_PERCENT)
            msg = (
                f"🟢 *LONG · FVG (Tendencia)*\n"
                f"Par: `{clean_symbol}`\n"
                f"Rebote FVG: `{v1_high_p:.4f}`\n"
                f"Stop Loss: `{sl:.4f}` | TP: `{tp1:.4f}`"
            )
            send_telegram(msg)

        if rebote_bearish and tendencia_bajista and volumen_alto:
            sl = v1_low_p * (1 + SL_PERCENT)
            tp1 = c_close * (1 - TP1_PERCENT)
            msg = (
                f"🔴 *SHORT · FVG (Tendencia)*\n"
                f"Par: `{clean_symbol}`\n"
                f"Rebote FVG: `{v3_high_p:.4f}`\n"
                f"Stop Loss: `{sl:.4f}` | TP: `{tp1:.4f}`"
            )
            send_telegram(msg)

    except Exception as e:
        pass

async def bucle_bot():
    print("Bot Dual Sincronizado activado.")
    send_telegram("🎯 *Bot Sincronizado con FVG V3*\nParámetros de ATR (10), Barrido (96), RSI/Bollinger y Doble Estrategia activos.")
    
    while True:
        for symbol in SYMBOLS:
            run_strategy_for_symbol(symbol)
            await asyncio.sleep(0.03)
        
        await asyncio.sleep(20)

async def handle_ping(request):
    return web.Response(text="Bot activo")

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
