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
LIMIT_SWEEP = 96
RECENT_WINDOW = 20
SL_PERCENT = 0.050
TP1_PERCENT = 0.007  # 0.7%
TP2_PERCENT = 0.015  # 1.5%
MAX_VALIDEZ_ATR = 10.0

# Registro para evitar duplicados en la misma vela
sent_signals = set()

SYMBOLS = [
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
    "DENT/USDT", "KEY/USDT", "TWT/USDT", "COS/USDT", "CTXC/USDT"
]

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

    last_candle_time = df["time"].iloc[-1]
    signal_key = f"{symbol}_{timeframe}_{last_candle_time}"
    if signal_key in sent_signals:
      return

    # --- ATR ---
    high_low = df["high"] - df["low"]
    high_close = (df["high"] - df["close"].shift()).abs()
    low_close = (df["low"] - df["close"].shift()).abs()
    true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    df["atr"] = true_range.rolling(window=14).mean()
    atr_val = df["atr"].iloc[-1]

    # --- FILTRO SWEEP ---
    min_previo = df["low"].iloc[-(LIMIT_SWEEP + RECENT_WINDOW) : -RECENT_WINDOW].min()
    max_previo = df["high"].iloc[-(LIMIT_SWEEP + RECENT_WINDOW) : -RECENT_WINDOW].max()
    
    swept_low = df["low"].iloc[-RECENT_WINDOW:].min() < min_previo
    swept_high = df["high"].iloc[-RECENT_WINDOW:].max() > max_previo

    # --- RECUADRO FVG (Velas v1, v2, v3) ---
    v1_high = df["high"].iloc[-3]
    v1_low = df["low"].iloc[-3]
    v3_low = df["low"].iloc[-1]
    v3_high = df["high"].iloc[-1]

    fvg_bullish = v3_low > v1_high
    fvg_bearish = v3_high < v1_low
    fvg_gap = (v3_low - v1_high if fvg_bullish else (v1_low - v3_high if fvg_bearish else 0))
    fvg_valido = (fvg_gap > 0) and (fvg_gap <= atr_val * MAX_VALIDEZ_ATR)

    # --- TAMAÑO DE VELA IMPULSIVA (%) ---
    size_v1 = ((df["high"].iloc[-3] - df["low"].iloc[-3]) / df["low"].iloc[-3] * 100)
    size_v2 = ((df["high"].iloc[-2] - df["low"].iloc[-2]) / df["low"].iloc[-2] * 100)
    size_v3 = ((df["high"].iloc[-1] - df["low"].iloc[-1]) / df["low"].iloc[-1] * 100)
    max_setup_size = max(size_v1, size_v2, size_v3)

    velas_tienen_rango = max_setup_size >= min_candle_size_pct
    clean_symbol = symbol.replace("/", "") + ".P"

    # --- SEÑAL LONG (Límites exactos del recuadro FVG) ---
    if fvg_bullish and fvg_valido and swept_low and velas_tienen_rango:
      fvg_bottom = v1_high
      fvg_top = v3_low
      fvg_mid = (fvg_bottom + fvg_top) / 2.0  # Entrada 1: 50% FVG
      fvg_final = fvg_bottom                 # Entrada 2: Final FVG (Borde del recuadro)
      
      sl = v1_low * (1 - SL_PERCENT)
      tp1 = fvg_final * (1 + TP1_PERCENT)
      tp2 = fvg_final * (1 + TP2_PERCENT)

      msg = (
          f"🟢 *LONG · FVG ({timeframe})*\n"
          f"Par: `{clean_symbol}`\n"
          f"Rango Vela: `{max_setup_size:.2f}%`\n"
          f"📍 Entrada 1 (50% FVG): `{fvg_mid:.4f}`\n"
          f"📍 Entrada 2 (Final FVG): `{fvg_final:.4f}`\n"
          f"🎯 TP1 (0.7%): `{tp1:.4f}` | TP2 (1.5%): `{tp2:.4f}`\n"
          f"🛑 SL: `{sl:.4f}`"
      )
      send_telegram(msg)
      sent_signals.add(signal_key)

    # --- SEÑAL SHORT (Límites exactos del recuadro FVG) ---
    if fvg_bearish and fvg_valido and swept_high and velas_tienen_rango:
      fvg_bottom = v3_high
      fvg_top = v1_low
      fvg_mid = (fvg_bottom + fvg_top) / 2.0  # Entrada 1: 50% FVG
      fvg_final = fvg_top                    # Entrada 2: Final FVG (Borde del recuadro)
      
      sl = v1_high * (1 + SL_PERCENT)
      tp1 = fvg_final * (1 - TP1_PERCENT)
      tp2 = fvg_final * (1 - TP2_PERCENT)

      msg = (
          f"🔴 *SHORT · FVG ({timeframe})*\n"
          f"Par: `{clean_symbol}`\n"
          f"Rango Vela: `{max_setup_size:.2f}%`\n"
          f"📍 Entrada 1 (50% FVG): `{fvg_mid:.4f}`\n"
          f"📍 Entrada 2 (Final FVG): `{fvg_final:.4f}`\n"
          f"🎯 TP1 (0.7%): `{tp1:.4f}` | TP2 (1.5%): `{tp2:.4f}`\n"
          f"🛑 SL: `{sl:.4f}`"
      )
      send_telegram(msg)
      sent_signals.add(signal_key)

    if len(sent_signals) > 1000:
      sent_signals.clear()

  except Exception as e:
    print(f"⚠️ Error procesando {symbol} en {timeframe}: {e}", flush=True)

async def bucle_bot():
  send_telegram("⏰ *Bot FVG V3 Activo (Precios FVG Corregidos)*\nEscaneando 5m y 15m.")

  while True:
    now = datetime.now(timezone.utc)
    seconds_to_next_5m = 300 - ((now.minute % 5) * 60 + now.second)
    sleep_time = seconds_to_next_5m + 2

    if sleep_time < 5:
      sleep_time += 300

    await asyncio.sleep(sleep_time)

    now_awoke = datetime.now(timezone.utc)
    es_cuarto_de_hora = now_awoke.minute % 15 == 0

    print(f"[{now_awoke.strftime('%H:%M:%S')}] Escaneando 5m...", flush=True)
    for symbol in SYMBOLS:
      run_reversion_strategy(symbol, "5m", 2.0)
      await asyncio.sleep(0.04)

    if es_cuarto_de_hora:
      print(f"[{now_awoke.strftime('%H:%M:%S')}] Escaneando 15m...", flush=True)
      for symbol in SYMBOLS:
        run_reversion_strategy(symbol, "15m", 3.0)
        await asyncio.sleep(0.04)

async def handle_ping(request):
  return web.Response(text="Bot FVG V3 Activo")

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
