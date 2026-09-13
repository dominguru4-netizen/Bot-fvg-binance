import time
import os
import ccxt
import pandas as pd
import requests
from aiohttp import web
import asyncio
from datetime import datetime, timezone

# ==========================================
# CREDENCIALES TELEGRAM
# ==========================================
TELEGRAM_TOKEN = "8638598049:AAEcQ2kjt9qM_PywnFTZs-2mY-3O8ahW-B0"
TELEGRAM_CHAT_ID = "2118999160"

# ==========================================
# PARÁMETROS GLOBALES
# ==========================================
LIMIT_SWEEP = 96          
SL_PERCENT = 0.050        
TP1_PERCENT = 0.007       
MAX_VALIDEZ_ATR = 10.0    

# LISTA DE PARES DE FUTUROS
SYMBOLS = [
    'H/USDT', 'SKYAI/USDT', 'BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'BNB/USDT', 'XRP/USDT', 'ADA/USDT', 'AVAX/USDT', 'DOGE/USDT', 'DOT/USDT', 'LINK/USDT',
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
    except Exception as e:
        print(f"Error Telegram: {e}")

def run_reversion_strategy(symbol, timeframe, min_candle_size_pct):
    try:
        bars = exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=150)
        if not bars or len(bars) < 120:
            return
            
        df = pd.DataFrame(bars, columns=['time', 'open', 'high', 'low', 'close', 'volume'])
        
        # Eliminar la vela actual abierta (a medias)
        df = df.iloc[:-1].copy()
        
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

        high_low = df['high'] - df['low']
        high_close = (df['high'] - df['close'].shift()).abs()
        low_close = (df['low'] - df['close'].shift()).abs()
        true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        df['atr'] = true_range.rolling(window=14).mean()

        # Velas de referencia para el cierre
        c_high = df['high'].iloc[-1]
        c_low = df['low'].iloc[-1]
        atr_val = df['atr'].iloc[-1]
        
        # --- FVG REVERSIÓN ---
        v1_high = df['high'].iloc[-3]
        v1_low = df['low'].iloc[-3]
        v3_low = df['low'].iloc[-1]
        v3_high = df['high'].iloc[-1]

        fvg_bullish = v3_low > v1_high
        fvg_bearish = v3_high < v1_low
        fvg_gap = v3_low - v1_high if fvg_bullish else (v1_low - v3_high if fvg_bearish else 0)
        fvg_valido = (fvg_gap > 0) and (fvg_gap <= atr_val * MAX_VALIDEZ_ATR)

        # Filtro de barrido
        min_previo = df['low'].iloc[-(LIMIT_SWEEP+5):-5].min()
        max_previo = df['high'].iloc[-(LIMIT_SWEEP+5):-5].max()
        swept_low = df['low'].iloc[-5:].min() < min_previo
        swept_high = df['high'].iloc[-5:].max() > max_previo

        # Extremos RSI/BB
        oversold = (df['rsi'].iloc[-1] < 35) or (c_low <= df['bb_lower'].iloc[-1])
        overbought = (df['rsi'].iloc[-1] > 65) or (c_high >= df['bb_upper'].iloc[-1])

        # --- NUEVO FILTRO: Tamaño de la vela que rompe (%) ---
        # Verificamos la volatilidad de las últimas 3 velas (V1, V2, V3 del FVG)
        size_v1 = (df['high'].iloc[-3] - df['low'].iloc[-3]) / df['low'].iloc[-3] * 100
        size_v2 = (df['high'].iloc[-2] - df['low'].iloc[-2]) / df['low'].iloc[-2] * 100
        size_v3 = (df['high'].iloc[-1] - df['low'].iloc[-1]) / df['low'].iloc[-1] * 100
        max_setup_size = max(size_v1, size_v2, size_v3)
        
        velas_tienen_rango = max_setup_size >= min_candle_size_pct

        clean_symbol = symbol.replace('/', '') + '.P'
        
        # --- LOGS DIAGNÓSTICO ---
        if clean_symbol in ['HUSDT.P', 'SKYAIUSDT.P']:
            print(f"[{clean_symbol} | {timeframe}] Rango Max FVG: {max_setup_size:.2f}% (Req: {min_candle_size_pct}%) | Valido: {velas_tienen_rango}")

        # --- DISPAROS REVERSIÓN ---
        if fvg_bullish and fvg_valido and swept_low and oversold and velas_tienen_rango:
            sl = v1_high * (1 - SL_PERCENT)
            tp1 = v1_high * (1 + TP1_PERCENT)
            msg = f"🟢 *LONG · FVG ({timeframe})*\nPar: `{clean_symbol}`\nRango Vela: `{max_setup_size:.2f}%`\nEntrada: `{v1_high:.4f}`\nSL: `{sl:.4f}` | TP: `{tp1:.4f}`"
            send_telegram(msg)
            
        if fvg_bearish and fvg_valido and swept_high and overbought and velas_tienen_rango:
            sl = v1_low * (1 + SL_PERCENT)
            tp1 = v1_low * (1 - TP1_PERCENT)
            msg = f"🔴 *SHORT · FVG ({timeframe})*\nPar: `{clean_symbol}`\nRango Vela: `{max_setup_size:.2f}%`\nEntrada: `{v3_high:.4f}`\nSL: `{sl:.4f}` | TP: `{tp1:.4f}`"
            send_telegram(msg)

    except Exception as e:
        pass

async def bucle_bot():
    send_telegram("⏰ *Bot Reversión Iniciado*\nEscaneando 5m (Rango > 2%) y 15m (Rango > 3%).")
    
    while True:
        now = datetime.now(timezone.utc)
        
        # Calcular segundos para el próximo múltiplo de 5 minutos
        seconds_to_next_5m = 300 - ((now.minute % 5) * 60 + now.second)
        sleep_time = seconds_to_next_5m + 3 # Margen de 3 segundos para asegurar cierre
        
        if sleep_time < 5:
            sleep_time += 300
            
        await asyncio.sleep(sleep_time)
        
        # Volvemos a leer la hora tras despertar para saber exactamente en qué minuto estamos
        now_awoke = datetime.now(timezone.utc)
        es_cuarto_de_hora = (now_awoke.minute % 15 == 0)
        
        print(f"[{now_awoke.strftime('%H:%M:%S')}] Iniciando escaneo de 5m...")
        for symbol in SYMBOLS:
            run_reversion_strategy(symbol, '5m', 3.8)
            await asyncio.sleep(0.05)
            
        if es_cuarto_de_hora:
            print(f"[{now_awoke.strftime('%H:%M:%S')}] Iniciando escaneo de 15m...")
            for symbol in SYMBOLS:
                run_reversion_strategy(symbol, '15m', 5.1)
                await asyncio.sleep(0.05)

async def handle_ping(request):
    return web.Response(text="Bot Reversión Activo (5m y 15m)")

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
