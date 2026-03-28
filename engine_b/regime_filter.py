import yfinance as yf
from ta.trend import EMAIndicator

def get_market_regime() -> str:
    """
    Determines the market regime by checking if the Nifty 50 index
    is above or below its 200-day EMA.
    """
    try:
        nifty_data = yf.download("^NSEI", period="1y", interval="1d", progress=False)
        if nifty_data.empty or len(nifty_data) < 200:
            return "UNKNOWN" # Not enough data

        close = nifty_data['Close'].squeeze() # Ensure it's a Series
        ema200 = EMAIndicator(close, window=200).ema_indicator().iloc[-1]
        current_price = close.iloc[-1]

        if current_price < ema200:
            return "BEARISH"
        return "BULLISH"
    except Exception as e:
        print(f"Error in get_market_regime: {e}")
        return "UNKNOWN"
