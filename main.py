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
# PARÁMETROS DE LA ESTRATEGIA
# ==========================================
TIMEFRAME = '5m'          
LIMIT_SWEEP = 96        
SL_PERCENT = 0.050        # Stop Loss al 5%
TP1_PERCENT = 0.007       # Take Profit al 0.7%
TP2_PERCENT = 0.015       # Take Profit 2 al 1.5%

# LISTA DE PARES FUTUROS PERPETUOS (USDT)
SYMBOLS = [
    'BTC/USDT:USDT', 'ETH/USDT:USDT', 'SOL/USDT:USDT', 'BNB/USDT:USDT', 'XRP/USDT:USDT', 'ADA/USDT:USDT', 'AVAX/USDT:USDT', 'DOGE/USDT:USDT', 'DOT/USDT:USDT', 'LINK/USDT:USDT',
    'NEAR/USDT:USDT', 'SUI/USDT:USDT', 'PEPE/USDT:USDT', 'SHIB/USDT:USDT', 'LTC/USDT:USDT', 'UNI/USDT:USDT', 'APT/USDT:USDT', 'BCH/USDT:USDT', 'ICP/USDT:USDT', 'FET/USDT:USDT',
    'RENDER/USDT:USDT', 'ETC/USDT:USDT', 'FIL/USDT:USDT', 'XMR/USDT:USDT', 'TIA/USDT:USDT', 'ATOM/USDT:USDT', 'STX/USDT:USDT', 'INJ/USDT:USDT', 'WIF/USDT:USDT', 'OP/USDT:USDT',
    'ARB/USDT:USDT', 'THETA/USDT:USDT', 'GRT/USDT:USDT', 'RUNE/USDT:USDT', 'FTM/USDT:USDT', 'SEI/USDT:USDT', 'FLOKI/USDT:USDT', 'BONK/USDT:USDT', 'JUP/USDT:USDT', 'AAVE/USDT:USDT',
    'MKR/USDT:USDT', 'ORDI/USDT:USDT', 'EGLD/USDT:USDT', 'SAND/USDT:USDT', 'EOS/USDT:USDT', 'MANA/USDT:USDT', 'XTZ/USDT:USDT', 'ALGO/USDT:USDT', 'FLOW/USDT:USDT', 'AXS/USDT:USDT',
    'GALA/USDT:USDT', 'SNX/USDT:USDT', 'NEO/USDT:USDT', 'KAVA/USDT:USDT', 'ROSE/USDT:USDT', 'CHZ/USDT:USDT', 'IOTA/USDT:USDT', 'MINA/USDT:USDT', 'COMP/USDT:USDT', 'CRV/USDT:USDT',
    'ZEC/USDT:USDT', 'KSM/USDT:USDT', 'DASH/USDT:USDT', '1INCH/USDT:USDT', 'ENJ/USDT:USDT', 'BAT/USDT:USDT', 'WOO/USDT:USDT', 'GMT/USDT:USDT', 'LRC/USDT:USDT', 'DYDX/USDT:USDT',
    'CFX/USDT:USDT', 'CKB/USDT:USDT', 'AR/USDT:USDT', 'BLUR/USDT:USDT', 'ARKM/USDT:USDT', 'STRK/USDT:USDT', 'ENA/USDT:USDT', 'TNSR/USDT:USDT', 'W/USDT:USDT', 'OM/USDT:USDT',
    'BOME/USDT:USDT', 'NOT/USDT:USDT', 'IO/USDT:USDT', 'ZK/USDT:USDT', 'ZRO/USDT:USDT', 'TURBO/USDT:USDT', 'LISTA/USDT:USDT', 'DOGS/USDT:USDT', 'CATI/USDT:USDT', 'HMSTR/USDT:USDT',
    'EIGEN/USDT:USDT', 'NEIRO/USDT:USDT', 'MEW/USDT:USDT', 'MEME/USDT:USDT', 'BEAM/USDT:USDT', 'RONIN/USDT:USDT', 'PIXEL/USDT:USDT', 'ALT/USDT:USDT', 'MANTA/USDT:USDT', 'XAI/USDT:USDT',
    'ACE/USDT:USDT', 'NFP/USDT:USDT', 'AI/USDT:USDT', 'PORTAL/USDT:USDT', 'AEVO/USDT:USDT', 'ETHFI/USDT:USDT', 'SAGA/USDT:USDT', 'OMNI/USDT:USDT', 'REZ/USDT:USDT', 'BB/USDT:USDT',
    'BANANA/USDT:USDT', 'SYN/USDT:USDT', 'PENDLE/USDT:USDT', 'CELO/USDT:USDT', 'ONE/USDT:USDT', 'HOT/USDT:USDT', 'ZIL/USDT:USDT', 'RVN/USDT:USDT', 'ANKR/USDT:USDT', 'AUDIO/USDT:USDT',
    'LDO/USDT:USDT', 'STORJ/USDT:USDT', 'SKL/USDT:USDT', 'ICX/USDT:USDT', 'ZRX/USDT:USDT', 'ONT/USDT:USDT', 'WAXP/USDT:USDT', 'SPELL/USDT:USDT', 'SLP/USDT:USDT', 'ALPHA/USDT:USDT',
    'COTI/USDT:USDT', 'ZEN/USDT:USDT', 'STRAX/USDT:USDT', 'SXP/USDT:USDT', 'C98/USDT:USDT', 'CHR/USDT:USDT', 'OXT/USDT:USDT', 'NMR/USDT:USDT', 'TRB/USDT:USDT', 'BAND/USDT:USDT',
    'RLC/USDT:USDT', 'API3/USDT:USDT', 'TRU/USDT:USDT', 'BADGER/USDT:USDT', 'POND/USDT:USDT', 'PERP/USDT:USDT', 'ALICE/USDT:USDT', 'SUPER/USDT:USDT', 'UNFI/USDT:USDT', 'LIT/USDT:USDT',
    'SFP/USDT:USDT', 'DODO/USDT:USDT', 'BEL/USDT:USDT', 'CTSI/USDT:USDT', 'DAR/USDT:USDT', 'MOVR/USDT:USDT', 'SYS/USDT:USDT', 'PEOPLE/USDT:USDT', 'ACH/USDT:USDT', 'AGLD/USDT:USDT',
    'GLMR/USDT:USDT', 'ASTR/USDT:USDT', 'BSW/USDT:USDT', 'CVX/USDT:USDT', 'FIS/USDT:USDT', 'STPT/USDT:USDT', 'RAD/USDT:USDT', 'T/USDT:USDT', 'PROS/USDT:USDT', 'VTHO/USDT:USDT',
    'WRX/USDT:USDT', 'MBL/USDT:USDT', 'DENT/USDT:USDT', 'KEY/USDT:USDT', 'TWT/USDT:USDT', 'COS/USDT:USDT', 'CTXC/USDT:USDT'
]

exchange = ccxt.binance({
    'enableRateLimit': True,
    'options': {'defaultType': 'future'}
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
        bars = exchange.fetch_ohlcv(symbol, timeframe=TIMEFRAME, limit=200)
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

        # EMA 27 para tendencias más reactivas
        df['ema_27'] = df['close'].rolling(window=27).mean()
        df['vol_sma'] = df['volume'].rolling(window=20).mean()

        # ATR para Banda Máxima de Validez
        high_low = df['high'] - df['low']
        high_close = (df['high'] - df['close'].shift()).abs()
        low_close = (df['low'] - df['close'].shift()).abs()
        true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        df['atr'] = true_range.rolling(window=14).mean()

        # --- VARIABLES ACTUALES ---
        c_close = df['close'].iloc[-2]
        c_high = df['high'].iloc[-2]
        c_low = df['low'].iloc[-2]
        c_vol = df['volume'].iloc[-2]
        ema_val = df['ema_27'].iloc[-2]
        atr_val = df['atr'].iloc[-2]
        
        # --- FVG RECIENTE (Para Reversión Clásica) ---
        v3_low = df['low'].iloc[-2]
        v1_high = df['high'].iloc[-4]
        v3_high = df['high'].iloc[-2]
        v1_low = df['low'].iloc[-4]

        fvg_bullish = v3_low > v1_high
        fvg_bearish = v3_high < v1_low
        fvg_gap = v3_low - v1_high if fvg_bullish else (v1_low - v3_high if fvg_bearish else 0)
        fvg_valido = (fvg_gap > 0) and (fvg_gap <= atr_val * 10.0)

        # --- FVG ANTERIOR (Para Mitigación/Rebote de Tendencia) ---
        v3_low_prev = df['low'].iloc[-3]
        v1_high_prev = df['high'].iloc[-5]
        v3_high_prev = df['high'].iloc[-3]
        v1_low_prev = df['low'].iloc[-5]

        fvg_bullish_prev = v3_low_prev > v1_high_prev
        fvg_bearish_prev = v3_high_prev < v1_low_prev
        fvg_gap_prev = v3_low_prev - v1_high_prev if fvg_bullish_prev else (v1_low_prev - v3_high_prev if fvg_bearish_prev else 0)
        fvg_valido_prev = (fvg_gap_prev > 0) and (fvg_gap_prev <= atr_val * 10.0)

        # Lógica de Rebote (Mitigación): La vela actual toca la zona del FVG anterior pero cierra respetándola
        rebote_bullish = fvg_bullish_prev and fvg_valido_prev and (c_low <= v3_low_prev) and (c_close > v1_high_prev)
        rebote_bearish = fvg_bearish_prev and fvg_valido_prev and (c_high >= v3_high_prev) and (c_close < v1_low_prev)

        # --- CONDICIONES DE ENTORNO ---
        min_previo = df['low'].iloc[-(LIMIT_SWEEP+2):-2].min()
        max_previo = df['high'].iloc[-(LIMIT_SWEEP+2):-2].max()
        swept_low = c_low < min_previo
        swept_high = c_high > max_previo
        oversold = (df['rsi'].iloc[-2] < 35) or (c_low <= df['bb_lower'].iloc[-2])
        overbought = (df['rsi'].iloc[-2] > 65) or (c_high >= df['bb_upper'].iloc[-2])

        tendencia_alcista = c_close > ema_val
        tendencia_bajista = c_close < ema_val
        volumen_alto = c_vol > (df['vol_sma'].iloc[-2] * 1.2)

        clean_symbol = symbol.split(':')[0]

        # 1. EVALUAR SEÑALES LONG
        if fvg_bullish and fvg_valido and swept_low and oversold:
            sl = v1_high * (1 - SL_PERCENT)
            tp1 = v1_high * (1 + TP1_PERCENT)
            msg = (
                f"🚀 *LONG (REVERSIÓN): {clean_symbol}*\n\n"
                f"🧲 *Zona FVG:* ${v1_high:.4f} - ${v3_low:.4f}\n"
                f"🛡 *Stop Loss (5%):* ${sl:.4f}\n"
                f"🎯 *Take Profit (0.7%):* ${tp1:.4f}\n"
                f"⚡ *Estrategia:* Barrido + Bollinger/RSI"
            )
            send_telegram(msg)
            
        elif rebote_bullish and tendencia_alcista and volumen_alto:
            sl = v1_high_prev * (1 - SL_PERCENT)
            tp1 = c_close * (1 + TP1_PERCENT)
            msg = (
                f"🚀 *LONG (REBOTE EN TENDENCIA): {clean_symbol}*\n\n"
                f"🧲 *Toque en FVG:* ${v1_high_prev:.4f} - ${v3_low_prev:.4f}\n"
                f"🛡 *Stop Loss (5%):* ${sl:.4f}\n"
                f"🎯 *Take Profit (0.7%):* ${tp1:.4f}\n"
                f"⚡ *Estrategia:* EMA 27 + Mitigación FVG + Volumen"
            )
            send_telegram(msg)

        # 2. EVALUAR SEÑALES SHORT
        if fvg_bearish and fvg_valido and swept_high and overbought:
            sl = v1_low * (1 + SL_PERCENT)
            tp1 = v1_low * (1 - TP1_PERCENT)
            msg = (
                f"🔻 *SHORT (REVERSIÓN): {clean_symbol}*\n\n"
                f"🧲 *Zona FVG:* ${v3_high:.4f} - ${v1_low:.4f}\n"
                f"🛡 *Stop Loss (5%):* ${sl:.4f}\n"
                f"🎯 *Take Profit (0.7%):* ${tp1:.4f}\n"
                f"⚡ *Estrategia:* Barrido + Bollinger/RSI"
            )
            send_telegram(msg)
            
        elif rebote_bearish and tendencia_bajista and volumen_alto:
            sl = v1_low_prev * (1 + SL_PERCENT)
            tp1 = c_close * (1 - TP1_PERCENT)
            msg = (
                f"🔻 *SHORT (REBOTE EN TENDENCIA): {clean_symbol}*\n\n"
                f"🧲 *Toque en FVG:* ${v3_high_prev:.4f} - ${v1_low_prev:.4f}\n"
                f"🛡 *Stop Loss (5%):* ${sl:.4f}\n"
                f"🎯 *Take Profit (0.7%):* ${tp1:.4f}\n"
                f"⚡ *Estrategia:* EMA 27 + Mitigación FVG + Volumen"
            )
            send_telegram(msg)

    except Exception:
        pass

async def bucle_bot():
    print("Bot FVG Dual activado en Render.")
    send_telegram("🤖 *Bot FVG Dual actualizado.*\nEstrategias activas: Reversión Clásica y Rebote en Tendencia (EMA 27).")
    
    while True:
        print(f"\n--- Escaneando Futuros Perpetuos ({time.strftime('%H:%M:%S')}) ---")
        for symbol in SYMBOLS:
            run_strategy_for_symbol(symbol)
            await asyncio.sleep(0.15)
        
        print("Escaneo finalizado. Esperando al siguiente ciclo...")
        await asyncio.sleep(60)

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
