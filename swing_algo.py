import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime
import os

# --- CONFIGURATION ---
PORTFOLIO_FILE = "mock_portfolio.csv"
CAPITAL_PER_TRADE = 200000

# List of Nifty 50 + Next 50 (Sample - you can expand this list)
NIFTY_100 = [
    "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "ICICIBANK.NS", "INFY.NS", 
    "HINDUNILVR.NS", "ITC.NS", "SBIN.NS", "BHARTIARTL.NS", "BAJFINANCE.NS",
    "ADANIENT.NS", "TATAMOTORS.NS", "SUNPHARMA.NS", "AXISBANK.NS", "TITAN.NS",
    "DMART.NS", "HAL.NS", "CANBK.NS", "PNB.NS", "ZOMATO.NS", "TRENT.NS"
]

# --- CORE FUNCTIONS ---
def get_signals(symbol):
    try:
        df = yf.download(symbol, period="1y", interval="1d", progress=False)
        if len(df) < 50: return None
        
        # Calculate Indicators directly (Replaces pandas_ta)
        df['EMA20'] = df['Close'].ewm(span=20, adjust=False).mean()
        df['EMA50'] = df['Close'].ewm(span=50, adjust=False).mean()
        
        # RSI (14) using Wilder's Smoothing
        delta = df['Close'].diff()
        gain = delta.where(delta > 0, 0).ewm(alpha=1/14, adjust=False).mean()
        loss = (-delta.where(delta < 0, 0)).ewm(alpha=1/14, adjust=False).mean()
        rs = gain / loss
        df['RSI'] = 100 - (100 / (1 + rs))
        
        # OBV
        df['OBV'] = (np.sign(delta) * df['Volume']).fillna(0).cumsum()
        
        # ATR (14)
        high_low = df['High'] - df['Low']
        high_close = (df['High'] - df['Close'].shift()).abs()
        low_close = (df['Low'] - df['Close'].shift()).abs()
        true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        df['ATR'] = true_range.ewm(alpha=1/14, adjust=False).mean()
        
        last = df.iloc[-1]
        prev = df.iloc[-2]
        
        # Logic Parameters
        price = float(last['Close'])
        ema20 = float(last['EMA20'])
        ema50 = float(last['EMA50'])
        rsi = float(last['RSI'])
        atr = float(last['ATR'])
        obv_trend = df['OBV'].tail(3).is_monotonic_increasing
        
        # Decision Logic
        signal = "HOLD"
        if price > ema20 > ema50 and 45 < rsi < 65 and obv_trend:
            signal = "BUY"
        elif price < ema20:
            signal = "SELL"
            
        return {
            "Symbol": symbol,
            "Price": round(price, 2),
            "EMA20": round(ema20, 2),
            "RSI": round(rsi, 2),
            "ATR": round(atr, 2),
            "Signal": signal,
            "StopLoss": round(price - (2 * atr), 2)
        }
    except Exception as e:
        print(f"Error processing {symbol}: {e}")
        return None

# --- PORTFOLIO MANAGEMENT ---
def load_portfolio():
    if os.path.exists(PORTFOLIO_FILE):
        return pd.read_csv(PORTFOLIO_FILE)
    return pd.DataFrame(columns=["Symbol", "Entry_Price", "Qty", "Date", "StopLoss"])

def save_to_portfolio(symbol, price, sl):
    df = load_portfolio()
    qty = int(CAPITAL_PER_TRADE // price)
    new_row = pd.DataFrame([{
        "Symbol": symbol, "Entry_Price": price, 
        "Qty": qty, "Date": datetime.now().strftime("%Y-%m-%d"), "StopLoss": sl
    }])
    df = pd.concat([df, new_row], ignore_index=True)
    df.to_csv(PORTFOLIO_FILE, index=False)

# --- UI LAYOUT ---
st.set_page_config(page_title="Nifty Swing Algo", layout="wide")
st.title("📈 Nifty 50/Next 50 Swing Trading Algo")

tab1, tab2 = st.tabs(["Scanner", "Mock Portfolio"])

with tab1:
    st.header("Real-Time Market Scanner")
    if st.button("🚀 Run Analysis (Nifty 100)"):
        results = []
        progress_bar = st.progress(0)
        for i, stock in enumerate(NIFTY_100):
            data = get_signals(stock)
            if data: results.append(data)
            progress_bar.progress((i + 1) / len(NIFTY_100))
        
        res_df = pd.DataFrame(results)
        
        # Color coding signals
        def color_signal(val):
            color = 'green' if val == 'BUY' else 'red' if val == 'SELL' else 'white'
            return f'color: {color}'

        st.dataframe(res_df.style.map(color_signal, subset=['Signal']), use_container_width=True)
        
        # Execution Section
        st.subheader("Execute Mock Trade")
        selected_stock = st.selectbox("Select stock to BUY from scanner results", res_df[res_df['Signal'] == 'BUY']['Symbol'].tolist())
        if st.button("Confirm Mock Buy (₹2,00,000)"):
            stock_info = next(item for item in results if item["Symbol"] == selected_stock)
            save_to_portfolio(selected_stock, stock_info['Price'], stock_info['StopLoss'])
            st.success(f"Added {selected_stock} to Portfolio!")

with tab2:
    st.header("My Mock Trades (₹2L Capital)")
    port_df = load_portfolio()
    
    if not port_df.empty:
        # Fetch Live Prices for Portfolio
        live_data = []
        for symbol in port_df['Symbol']:
            ticker = yf.Ticker(symbol)
            live_price = ticker.history(period="1d")['Close'].iloc[-1]
            live_data.append(round(live_price, 2))
        
        port_df['Current_Price'] = live_data
        port_df['PnL'] = (port_df['Current_Price'] - port_df['Entry_Price']) * port_df['Qty']
        port_df['PnL_%'] = ((port_df['Current_Price'] - port_df['Entry_Price']) / port_df['Entry_Price']) * 100
        
        # Totals
        total_pnl = port_df['PnL'].sum()
        st.metric("Total Unrealized P&L", f"₹{total_pnl:,.2f}", f"{total_pnl/200000:.2%}")
        
        st.table(port_df.style.format({"PnL": "{:.2f}", "PnL_%": "{:.2f}%"}))
        
        if st.button("Reset Portfolio"):
            os.remove(PORTFOLIO_FILE)
            st.rerun()
    else:
        st.info("Portfolio is empty. Go to Scanner to find BUY signals.")