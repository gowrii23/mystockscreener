
import streamlit as st
import pandas as pd
import os

# --- Page Config ---
st.set_page_config(
    page_title="TradeFilter Dashboard",
    page_icon="◈",
    layout="wide",
)

# --- Data Loading ---
@st.cache_data(ttl=3600)
def load_data(file_path):
    if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
        try:
            if file_path.endswith('.jsonl'):
                return pd.read_json(file_path, lines=True)
            return pd.read_csv(file_path)
        except (ValueError, pd.errors.EmptyDataError):
            # Catches errors from pd.read_csv on empty or malformed files
            return pd.DataFrame()
    return pd.DataFrame()

qualified_universe_df = load_data("engine_a/output/qualified_universe.csv")
ranked_candidates_df = load_data("engine_b/output/ranked_candidates.csv")
audit_log_df = load_data("logs/audit_log.jsonl")

# --- UI Components ---

def display_metrics():
    st.header("◈ TradeFilter")
    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Universe", "500")
    col2.metric("Qualified", len(qualified_universe_df))
    col3.metric("Active Signals", len(ranked_candidates_df))
    col4.metric("Portfolio", "₹0") # Placeholder
    col5.metric("Alerts", "0") # Placeholder

def display_qualified_universe_tab():
    if not qualified_universe_df.empty:
        st.subheader("Fundamental Analysis Results")
        
        col1, col2 = st.columns([2, 1])

        with col1:
            st.info("These stocks have passed all fundamental checks (Quality, Safety, Valuation, Growth).")
            
            # Safely apply styling
            df_style = qualified_universe_df.style
            
            green_cols = ['l1_roce_3yr', 'l4_eps_cagr_3yr', 'l3_margin_of_safety']
            red_cols = ['l2_debt_equity']
            format_cols = green_cols + red_cols
            
            available_green = list(set(green_cols) & set(qualified_universe_df.columns))
            available_red = list(set(red_cols) & set(qualified_universe_df.columns))
            available_format = list(set(format_cols) & set(qualified_universe_df.columns))

            if available_green:
                df_style = df_style.background_gradient(cmap='Greens', subset=available_green)
            if available_red:
                df_style = df_style.background_gradient(cmap='Reds_r', subset=available_red)
            if available_format:
                df_style = df_style.format("{:.2f}", subset=available_format)

            st.dataframe(df_style)

        with col2:
            st.subheader("Margin of Safety")
            st.info("A higher margin of safety suggests a lower risk of overpaying for a stock.")
            if 'l3_margin_of_safety' in qualified_universe_df.columns and 'ticker' in qualified_universe_df.columns:
                chart_data = qualified_universe_df.set_index('ticker')[['l3_margin_of_safety']].dropna()
                if not chart_data.empty:
                    st.bar_chart(chart_data)
                else:
                    st.warning("Margin of Safety data is present but empty.")
            else:
                st.warning("Margin of Safety data not available.")

    else:
        st.warning("`qualified_universe.csv` not found or is empty. Please run Engine A to generate the list of fundamentally strong companies.")

def display_ranked_candidates_tab():
    if not ranked_candidates_df.empty:
        st.subheader("Momentum Scan Results")
        
        col1, col2 = st.columns([2, 1])

        with col1:
            st.info("These stocks showed strong momentum signals during the last scan.")
            
            # Safely apply styling
            df_style = ranked_candidates_df.style
            
            style_cols = ['l5_rsi', 'l5_volume_ratio']
            format_cols = style_cols + ['l5_ema20', 'l5_ema50', 'l5_ema200']

            available_style = list(set(style_cols) & set(ranked_candidates_df.columns))
            available_format = list(set(format_cols) & set(ranked_candidates_df.columns))
            
            if available_style:
                df_style = df_style.background_gradient(cmap='Greens', subset=available_style)
            if available_format:
                df_style = df_style.format("{:.2f}", subset=available_format)

            st.dataframe(df_style)
        
        with col2:
            st.subheader("Relative Strength Index (RSI)")
            st.info("RSI measures the speed and change of price movements. Values between 30 and 70 are often considered neutral.")
            if 'l5_rsi' in ranked_candidates_df.columns and 'ticker' in ranked_candidates_df.columns:
                chart_data = ranked_candidates_df.set_index('ticker')[['l5_rsi']].dropna()
                if not chart_data.empty:
                    st.bar_chart(chart_data)
                else:
                    st.warning("RSI data is present but empty.")
            else:
                st.warning("RSI data not available.")

    else:
        st.info("No active momentum signals. This could be because the market regime is not bullish, or no qualified stocks are showing momentum.")

def display_audit_log_tab():
    st.subheader("Execution Log")
    if not audit_log_df.empty:
        st.dataframe(audit_log_df)
    else:
        st.info("`audit_log.jsonl` not found or is empty.")

def main():
    display_metrics()
    
    st.markdown("---")
    
    tab1, tab2, tab3 = st.tabs(["Qualified Universe", "Ranked Candidates", "Audit Log"])

    with tab1:
        display_qualified_universe_tab()
    
    with tab2:
        display_ranked_candidates_tab()
    
    with tab3:
        display_audit_log_tab()

if __name__ == "__main__":
    main()
