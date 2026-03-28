import pandas as pd
import yfinance as yf
from ta.momentum import RSIIndicator
from ta.trend import EMAIndicator

def check_layer5(ticker: str, config: dict) -> tuple[bool, dict]:
    """
    Check for Layer 5: Momentum (The Trigger).
    """
    cfg = config['layer5_momentum']

    try:
        data = yf.download(ticker + ".NS", period="1y", interval="1d", progress=False)
        if data.empty or len(data) < 200:
            return False, {"reason": "insufficient_price_history"}

        close = data['Close'].squeeze()
        volume = data['Volume'].squeeze()

        ema20 = EMAIndicator(close, window=cfg['ema_short']).ema_indicator().iloc[-1]
        ema50 = EMAIndicator(close, window=cfg['ema_long']).ema_indicator().iloc[-1]
        ema200 = EMAIndicator(close, window=cfg['ema_trend_filter']).ema_indicator().iloc[-1]
        rsi = RSIIndicator(close, window=14).rsi().iloc[-1]
        vol_ratio = volume.iloc[-1] / volume.rolling(20).mean().iloc[-1]
        high_52w = close.rolling(252).max().iloc[-1]
        current = close.iloc[-1]

        # All conditions
        ema_cross = ema20 > ema50
        above_200 = current > ema200
        rsi_ok = cfg['rsi_min'] < rsi < cfg['rsi_max_entry']
        vol_ok = vol_ratio > cfg['volume_ratio_min']
        not_near_high = current < high_52w * (1 - cfg['high_52w_buffer_pct'] / 100)

        passes = ema_cross and above_200 and rsi_ok and vol_ok and not_near_high

        return passes, {
            "l5_ema20": round(ema20, 2), "l5_ema50": round(ema50, 2),
            "l5_ema200": round(ema200, 2), "l5_rsi": round(rsi, 1),
            "l5_volume_ratio": round(vol_ratio, 2),
            "l5_near_52w_high": bool(not not_near_high),
            "l5_ema_cross": bool(ema_cross), "l5_above_200ema": bool(above_200)
        }
    except Exception as e:
        return False, {"reason": f"error_in_l5: {e}"}
