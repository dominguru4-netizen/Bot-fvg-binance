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
# PARÁMETROS GLOBALES (FVG V3 - SOLO 3M)
# ==========================================
BB_LENGTH = 20
BB_STD = 2.0
RSI_LENGTH = 14
RSI_OVERBOUGHT = 65
RSI_OVERSOLD = 35

MAX_VALIDEZ_ATR = 10.0  
LOOKBACK_SWEEP = 40     # Velas hacia atrás para rastrear la secuencia

SL_PERCENT = 0.050      
TP1_PERCENT = 0.007     
TP2_PERCENT = 0.015     

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

def run_reversion_strategy(symbol, timeframe, min_candle_size_pct):
  try:
    bars = exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=150)
    if not bars or len(bars) < 120:
      return

    df = pd.DataFrame(
        bars, columns=["time", "open", "high", "low", "close", "volume"]
    )
    df = df.iloc[:-1].copy()
    n = len(df)

    last_candle_time = df["time"].iloc[-1]
    signal_key = f"{symbol}_{timeframe}_{last_candle_time}"
    if signal_key in sent_signals:
      return

    # --- 1. INDICADORES ---
    high_low = df["high"] - df["low"]
    high_close = (df["high"] - df["close"].shift()).abs()
    low_close = (df["low"] - df["close"].shift()).abs()
    true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    df["atr"] = true_range.rolling(window=14).mean()
    atr_val = df["atr"].iloc[-1]

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

    # --- 2. RASTREO: BARRIDO -> MITIGACIÓN CON CUERPO A FAVOR DEL BARRIDO ---
    long_state = "NONE"
    sweep_low_long = float('inf')

    short_state = "NONE"
    sweep_high_short = -float('inf')

    start_idx = max(0, n - LOOKBACK_SWEEP)

    for i in range(start_idx, n):
        # --- LÓGICA LONG ---
        is_sweep_long = (df['low'].iloc[i] <= df['lower_bb'].iloc[i]) and (df['rsi'].iloc[i] <= RSI_OVERSOLD)
        
        if is_sweep_long:
            long_state = "SWEEP"
            sweep_low_long = df['low'].iloc[i]  # Guarda la línea blanca (el mínimo)
            
        elif long_state == "SWEEP":
            # La vela cierra con CUERPO por DEBAJO de la línea blanca
            if df['close'].iloc[i] < sweep_low_long:
                long_state = "MITIGATED"

        # --- LÓGICA SHORT ---
        is_sweep_short = (df['high'].iloc[i] >= df['upper_bb'].iloc[i]) and (df['rsi'].iloc[i] >= RSI_OVERBOUGHT)
        
        if is_sweep_short:
            short_state = "SWEEP"
            sweep_high_short = df['high'].iloc[i] # Guarda la línea blanca (el máximo)
            
        elif short_state == "SWEEP":
            # La vela cierra con CUERPO por ENCIMA de la línea blanca
            if df['close'].iloc[i] > sweep_high_short:
                short_state = "MITIGATED"

    valid_long_sequence = (long_state == "MITIGATED")
    valid_short_sequence = (short_state == "MITIGATED")

    # --- 3. GATILLO: FORMACIÓN DEL FVG ---
    v1_high = df["high"].iloc[-3]
    v1_low = df["low"].iloc[-3]
    v3_low = df["low"].iloc[-1]
    v3_high = df["high"].iloc[-1]

    fvg_bullish = (v3_low > v1_high)
    fvg_bearish = (v3_high < v1_low)
    
    fvg_gap = (v3_low - v1_high if fvg_bullish else (v1_low - v3_high if fvg_bearish else 0))
    fvg_valido = (fvg_gap > 0) and (abs(current_close - ((v1_high + v3_low) / 2.0 if fvg_bullish else (v3_high + v1_low) / 2.0)) <= (atr_val * MAX_VALIDEZ_ATR))

    # --- 4. TAMAÑO VELA IMPULSIVA (%) ---
    size_v1 = ((df["high"].iloc[-3] - df["low"].iloc[-3]) / df["low"].iloc[-3] * 100)
    size_v2 = ((df["high"].iloc[-2] - df["low"].iloc[-2]) / df["low"].iloc[-2] * 100)
    size_v3 = ((df["high"].iloc[-1] - df["low"].iloc[-1]) / df["low"].iloc[-1] * 100)
    max_setup_size = max(size_v1, size_v2, size_v3)

    velas_tienen_rango = max_setup_size >= min_candle_size_pct
    clean_symbol = symbol.replace("/", "") + ".P"

    # --- 5. SEÑALES ---
    # LONG
    if valid_long_sequence and fvg_bullish and fvg_valido and velas_tienen_rango:
      fvg_bottom = v1_high
      fvg_top = v3_low
      fvg_mid = (fvg_bottom + fvg_top) / 2.0  
      fvg_final = fvg_bottom                 
      
      sl = v1_low * (1 - SL_PERCENT)
      tp1 = fvg_final * (1 + TP1_PERCENT)
      tp2 = fvg_final * (1 + TP2_PERCENT)

      msg = (
          f"🟢 *LONG · Secuencia FVG (3m)*\n"
          f"Par: `{clean_symbol}`\n"
          f"Rango Impulso: `{max_setup_size:.2f}%`\n"
          f"📍 Entrada 1 (50% FVG): `{fvg_mid:.6f}`\n"
          f"📍 Entrada 2 (Final FVG): `{fvg_final:.6f}`\n"
          f"🎯 TP1 (0.7%): `{tp1:.6f}` | TP2 (1.5%): `{tp2:.6f}`\n"
          f"🛑 SL (5%): `{sl:.6f}`"
      )
      send_telegram(msg)
      sent_signals.add(signal_key)

    # SHORT
    if valid_short_sequence and fvg_bearish and fvg_valido and velas_tienen_rango:
      fvg_bottom = v3_high
      fvg_top = v1_low
      fvg_mid = (fvg_bottom + fvg_top) / 2.0  
      fvg_final = fvg_top                    
      
      sl = v1_high * (1 + SL_PERCENT)
      tp1 = fvg_final * (1 - TP1_PERCENT)
      tp2 = fvg_final * (1 - TP2_PERCENT)

      msg = (
          f"🔴 *SHORT · Secuencia FVG (3m)*\n"
          f"Par: `{clean_symbol}`\n"
          f"Rango Impulso: `{max_setup_size:.2f}%`\n"
          f"📍 Entrada 1 (50% FVG): `{fvg_mid:.6f}`\n"
          f"📍 Entrada 2 (Final FVG): `{fvg_final:.6f}`\n"
          f"🎯 TP1 (0.7%): `{tp1:.6f}` | TP2 (1.5%): `{tp2:.6f}`\n"
          f"🛑 SL (5%): `{sl:.6f}`"
      )
      send_telegram(msg)
      sent_signals.add(signal_key)

    if len(sent_signals) > 1000:
      sent_signals.clear()

  except Exception as e:
    print(f"⚠️ Error procesando {symbol} en 3m: {e}", flush=True)

async def bucle_bot():
  send_telegram("⏰ *Bot FVG Corregido*\nRotura con cuerpo HASTA EL FONDO (para la toma de liquidez real) activa.")

  while True:
    now = datetime.now(timezone.utc)
    seconds_to_next_3m = 180 - ((now.minute % 3) * 60 + now.second)
    sleep_time = seconds_to_next_3m + 2

    if sleep_time < 5:
      sleep_time += 180

    await asyncio.sleep(sleep_time)
    print(f"[{datetime.now(timezone.utc).strftime('%H:%M:%S')}] Escaneando mercado (3m)...", flush=True)
    
    for symbol in SYMBOLS:
      run_reversion_strategy(symbol, "3m", 1.0)
      await asyncio.sleep(0.04)

async def handle_ping(request):
  return web.Response(text="Bot FVG Secuencia Toma Liquidez (3m) Activo")

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
