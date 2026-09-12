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
LIMIT_SWEEP = 96          # Ajustado a 96 velas como acordamos
SL_PERCENT = 0.050        
TP1_PERCENT = 0.007       

# LISTA DE PARES CON FORMATO DE FUTUROS (Sufijo .P / Futuros Binance)
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

# Inicializamos el exchange configurado para futuros perpetuos por defecto
exchange = ccxt.binance({
    'enableRateLimit': True,
    'options': {
        'defaultType': 'swap'  # Forzar tipo swap/perpetuo de Binance
    }
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
        # Descargar datos usando el formato de swap directo
        bars = exchange.fetch_ohlcv(symbol, timeframe=TIMEFRAME, limit=200)
        if not bars or len(bars) < 150:
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

        # --- VARIABLES ACTUALES ---
        c_close = df['close'].iloc[-2]
        c_high = df['high'].iloc[-2]
        c_low = df['low'].iloc[-2]
        c_vol = df['volume'].iloc[-2]
        ema_val = df['ema_27'].iloc[-2]
        atr_val = df['atr'].iloc[-2]
        
        # --- FVG RECIENTE (Reversión) ---
        v3_low = df['low'].iloc[-2]
        v1_high = df['high'].iloc[-4]
        v3_high = df['high'].iloc[-2]
        v1_low = df['low'].iloc[-4]

        fvg_bullish = v3_low > v1_high
        fvg_bearish = v3_high < v1_low
        fvg_gap = v3_low - v1_high if fvg_bullish else (v1_low - v3_high if fvg_bearish else 0)
        fvg_valido = (fvg_gap > 0) and (fvg_gap <= atr_val * 10.0)

        # --- FVG ANTERIOR (Tendencia) ---
        v3_low_prev = df['low'].iloc[-3]
        v1_high_prev = df['high'].iloc[-5]
        v3_high_prev = df['high'].iloc[-3]
        v1_low_prev = df['low'].iloc[-5]

        fvg_bullish_prev = v3_low_prev > v1_high_prev
        fvg_bearish_prev = v3_high_prev < v1_low_prev
        fvg_gap_prev = v3_low_prev - v1_high_prev if fvg_bullish_prev else (v1_low_prev - v3_high_prev if fvg_bearish_prev else 0)
        fvg_valido_prev = (fvg_gap_prev > 0) and (fvg_gap_prev <= atr_val * 10.0)

        rebote_bullish = fvg_bullish_prev and fvg_valido_prev and (c_low <= v3_low_prev) and (c_close > v1_high_prev)
        rebote_bearish = fvg_bearish_prev and fvg_valido_prev and (c_high >= v3_high_prev) and (c_close < v1_low_prev)

        # --- CONDICIONES DE ENTORNO (96 velas) ---
        min_previo = df['low'].iloc[-(LIMIT_SWEEP+2):-2].min()
        max_previo = df['high'].iloc[-(LIMIT_SWEEP+2):-2].max()
        swept_low = c_low < min_previo
        swept_high = c_high > max_previo
        oversold = (df['rsi'].iloc[-2] < 35) or (c_low <= df['bb_lower'].iloc[-2])
        overbought = (df['rsi'].iloc[-2] > 65) or (c_high >= df['bb_upper'].iloc[-2])

        tendencia_alcista = c_close > ema_val
        tendencia_bajista = c_close < ema_val
        volumen_alto = c_vol > (df['vol_sma'].iloc[-2] * 1.2)

        # Nombre estético para Telegram estilo .P
        clean_symbol = symbol.replace('/', '') + '.P'

        # 1. LONG REVERSIÓN
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
            
        # 2. LONG TENDENCIA
        elif rebote_bullish and tendencia_alcista and volumen_alto:
            sl = v1_high_prev * (1 - SL_PERCENT)
            tp1 = c_close * (1 + TP1_PERCENT)
            msg = (
                f"🟢 *LONG · FVG (Tendencia)*\n"
                f"Par: `{clean_symbol}`\n"
                f"Toque FVG previo: `{v1_high_prev:.4f}`\n"
                f"Stop Loss: `{sl:.4f}` | TP: `{tp1:.4f}`"
            )
            send_telegram(msg)

        # 3. SHORT REVERSIÓN
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
            
        # 4. SHORT TENDENCIA
        elif rebote_bearish and tendencia_bajista and volumen_alto:
            sl = v1_low_prev * (1 + SL_PERCENT)
            tp1 = c_close * (1 - TP1_PERCENT)
            msg = (
                f"🔴 *SHORT · FVG (Tendencia)*\n"
                f"Par: `{clean_symbol}`\n"
                f"Toque FVG previo: `{v3_high_prev:.4f}`\n"
                f"Stop Loss: `{sl:.4f}` | TP: `{tp1:.4f}`"
            )
            send_telegram(msg)

    except Exception as e:
        pass

async def bucle_bot():
    print("Bot FVG Masivo activado.")
    send_telegram("🤖 *Bot FVG Actualizado*\nModo de escaneo masivo con sufijo `.P` activado.")
    
    while True:
        print(f"\n--- Escaneando ciclo masivo ({time.strftime('%H:%M:%S')}) ---")
        for symbol in SYMBOLS:
            run_strategy_for_symbol(symbol)
            await asyncio.sleep(0.05) # Pausa ultra rápida para soltar alertas en cadena
        
        await asyncio.sleep(30) # Ciclos más cortos para revisar constantemente

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
