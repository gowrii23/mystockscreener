import time
import yfinance as yf
from audit_logger import audit_log

def fetch_with_retry(ticker: str, max_retries: int = 3) -> dict | None:
    for attempt in range(max_retries):
        try:
            stock = yf.Ticker(ticker + ".NS")
            info = stock.info
            if not info or info.get('regularMarketPrice') is None:
                raise ValueError(f"Empty data for {ticker}")
            
            # yfinance sometimes returns lists, we want the first element if so
            for key, value in info.items():
                if isinstance(value, list) and len(value) > 0:
                    info[key] = value[0]

            return info
        except Exception as e:
            wait = 2 ** attempt
            print(f"[{ticker}] Attempt {attempt+1} failed: {e}. Retrying in {wait}s...")
            time.sleep(wait)
    audit_log(ticker, "SKIPPED", "API_FAILURE_AFTER_RETRIES")
    return None

def fetch_history(ticker: str, period: str = "1y", interval: str = "1d"):
    stock = yf.Ticker(ticker + ".NS")
    return stock.history(period=period, interval=interval)

def fetch_financials(ticker: str):
    stock = yf.Ticker(ticker + ".NS")
    return stock.financials

def fetch_balance_sheet(ticker: str):
    stock = yf.Ticker(ticker + ".NS")
    return stock.balance_sheet

def fetch_cash_flow(ticker: str):
    stock = yf.Ticker(ticker + ".NS")
    return stock.cashflow

fetch_info = fetch_with_retry
