import asyncio
from datetime import datetime, timezone
import os
from aiohttp import web
import ccxt
import numpy as np
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

TP_PERCENT = 0.04  # +4%  (pendiente de definir regla real, se deja igual por ahora)
SL_PERCENT = 0.03  # -3%
WICK_AVG_LENGTH = 10   # nº de velas para calcular el tamaño "normal" de vela
WICK_MULTIPLIER = 1.5  # la vela que rompe la banda debe ser >= 1.5x esa media
MAX_SWEEP_CANDLES = 480      # 24 horas en velas de 3m
FVG_SEARCH_WINDOW = 60       # velas a buscar el primer FVG tras el barrido (~3h)

sent_signals = set()

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
        if not bars or len(bars) < 120:
            return
        df = pd.DataFrame(bars, columns=["time", "open", "high", "low", "close", "volume"]).iloc[:-1].copy()

        # ---- Indicadores base ----
        df["sma"] = df["close"].rolling(window=BB_LENGTH).mean()
        df["std"] = df["close"].rolling(window=BB_LENGTH).std(ddof=0)
        df["upper_bb"] = df["sma"] + (BB_STD * df["std"])
        df["lower_bb"] = df["sma"] - (BB_STD * df["std"])

        delta = df["close"].diff()
        gain = delta.where(delta > 0, 0.0)
        loss = -delta.where(delta < 0, 0.0)
        alpha = 1 / RSI_LENGTH
        df["avg_gain"] = gain.ewm(alpha=alpha, min_periods=RSI_LENGTH, adjust=False).mean()
        df["avg_loss"] = loss.ewm(alpha=alpha, min_periods=RSI_LENGTH, adjust=False).mean()
        # Evita división por cero cuando avg_loss = 0 (tendencia sin velas rojas)
        rs = df["avg_gain"] / df["avg_loss"].replace(0, np.nan)
        df["rsi"] = 100 - (100 / (1 + rs))
        df["rsi"] = df["rsi"].fillna(100)

        df["prev_close"] = df["close"].shift(1)
        df["tr"] = df[["high", "low", "prev_close"]].apply(
            lambda row: max(row["high"] - row["low"],
                             abs(row["high"] - row["prev_close"]),
                             abs(row["low"] - row["prev_close"])), axis=1
        )
        df["atr"] = df["tr"].rolling(window=14).mean()

        # ---- Tamaño de la vela (rango high-low) y su media de referencia ----
        df["candle_range"] = df["high"] - df["low"]
        # Media de referencia SIN incluir la propia vela (shift 1), para no
        # inflar la media con el tamaño de la vela que estamos evaluando.
        df["avg_candle_range"] = df["candle_range"].rolling(window=WICK_AVG_LENGTH).mean().shift(1)

        # ---- Recorremos buscando señales BOT-S confirmadas ----
        for i in range(30, len(df) - 1):
            prev_low = df["low"].iloc[i - 1]
            prev_high = df["high"].iloc[i - 1]
            prev_rsi = df["rsi"].iloc[i - 1]
            prev_lower = df["lower_bb"].iloc[i - 1]
            prev_upper = df["upper_bb"].iloc[i - 1]
            prev_candle_range = df["candle_range"].iloc[i - 1]
            prev_avg_range = df["avg_candle_range"].iloc[i - 1]

            c_open, c_close = df["open"].iloc[i], df["close"].iloc[i]

            # Vela de ruptura válida: al menos WICK_MULTIPLIER veces el tamaño "normal"
            valid_break_candle = (
                pd.notna(prev_avg_range) and prev_avg_range > 0
                and prev_candle_range >= WICK_MULTIPLIER * prev_avg_range
            )

            is_bot_s_long = (
                (prev_low < prev_lower) and (prev_rsi <= RSI_OVERSOLD)
                and (c_close > c_open) and valid_break_candle
            )
            is_bot_s_short = (
                (prev_high > prev_upper) and (prev_rsi >= RSI_OVERBOUGHT)
                and (c_close < c_open) and valid_break_candle
            )

            if not is_bot_s_long and not is_bot_s_short:
                continue

            direction = "LONG" if is_bot_s_long else "SHORT"
            sig_price = c_close
            extreme_val = prev_low if direction == "LONG" else prev_high

            # ---- 2. Barrido de liquidez (cierre más allá del extremo de la señal) ----
            swept = False
            sweep_idx = -1

            for j in range(i + 1, min(i + 1 + MAX_SWEEP_CANDLES, len(df))):
                j_close = df["close"].iloc[j]
                curr_atr = df["atr"].iloc[j]

                # Cancelación: el precio se va >3 ATR a favor antes de barrer
                if direction == "LONG" and (df["high"].iloc[j] - sig_price) > (3 * curr_atr):
                    break
                if direction == "SHORT" and (sig_price - df["low"].iloc[j]) > (3 * curr_atr):
                    break

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

            # ---- 3. Primer FVG que se forme tras el barrido (sin filtro de tamaño) ----
            # OJO: empieza en sweep_idx + 1, NO en sweep_idx, para que el hueco
            # se forme realmente con velas posteriores al barrido.
            fvg_found = False
            fvg_mid = 0.0
            fvg_k = None

            search_end = min(sweep_idx + 1 + FVG_SEARCH_WINDOW, len(df))
            for k in range(sweep_idx + 1, search_end):
                if k - 2 < 0:
                    continue
                if direction == "LONG":
                    if (df["low"].iloc[k] > df["high"].iloc[k - 2]) and (df["close"].iloc[k - 1] > df["open"].iloc[k - 1]):
                        fvg_mid = (df["high"].iloc[k - 2] + df["low"].iloc[k]) / 2.0
                        fvg_found = True
                        fvg_k = k
                        break
                else:
                    if (df["high"].iloc[k] < df["low"].iloc[k - 2]) and (df["close"].iloc[k - 1] < df["open"].iloc[k - 1]):
                        fvg_mid = (df["low"].iloc[k - 2] + df["high"].iloc[k]) / 2.0
                        fvg_found = True
                        fvg_k = k
                        break

            if not fvg_found:
                continue

            # Dedup por símbolo + dirección + vela del FVG (ya no dependemos
            # de "estar en las últimas 2 velas", que era lo que bloqueaba casi todo)
            seq_id = f"{symbol}_{direction}_{df['time'].iloc[fvg_k]}"
            if seq_id in sent_signals:
                continue

            tp_val = fvg_mid * (1 + TP_PERCENT) if direction == "LONG" else fvg_mid * (1 - TP_PERCENT)
            sl_val = fvg_mid * (1 - SL_PERCENT) if direction == "LONG" else fvg_mid * (1 + SL_PERCENT)

            msg = (
                f"📌 *Estrategia FVG V3 (3m)*\n"
                f"Par: `{symbol.replace('/', '')}.P`\n"
                f"Dirección: *{direction}*\n"
                f"📍 Entrada Límite (50% FVG): `{fvg_mid:.6f}`\n"
                f"🎯 TP (+4%): `{tp_val:.6f}`\n"
                f"🛑 SL (-3%): `{sl_val:.6f}`\n"
                f"✅ Señal BOT-S ➔ Barrido (cierre) ➔ Primer FVG tras el barrido"
            )
            send_telegram(msg)
            sent_signals.add(seq_id)

        if len(sent_signals) > 2000:
            sent_signals.clear()
    except Exception as e:
        print(f"Error en {symbol}: {e}", flush=True)


async def bucle_bot():
    send_telegram("🚀 *Bot FVG V3 Reiniciado (versión corregida)*\n✅ Bug de filtro de últimas velas eliminado.\n✅ Primer FVG post-barrido, cualquier tamaño.\n✅ Filtro de mecha de rechazo (1.5x media) añadido.")
    while True:
        now = datetime.now(timezone.utc)
        sleep_time = (180 - ((now.minute % 3) * 60 + now.second)) + 2
        if sleep_time < 5:
            sleep_time += 180
        await asyncio.sleep(sleep_time)
        for symbol in SYMBOLS:
            run_fvg_v3_strategy(symbol, "3m")
            await asyncio.sleep(0.04)


async def handle_ping(request):
    return web.Response(text="Bot FVG V3 Activo (corregido)")


async def main():
    app = web.Application()
    app.router.add_get("/", handle_ping)
    runner = web.AppRunner(app)
    await runner.setup()
    await web.TCPSite(runner, "0.0.0.0", int(os.environ.get("PORT", 10000))).start()
    asyncio.create_task(bucle_bot())
    while True:
        await asyncio.sleep(3600)


if __name__ == "__main__":
    asyncio.run(main())
