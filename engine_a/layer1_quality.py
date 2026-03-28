import pandas as pd
from data_fetcher import fetch_financials, fetch_balance_sheet, fetch_cash_flow

def get_3yr_avg_roce(financials, balance_sheet):
    """
    Calculates 3-year average ROCE.
    ROCE = EBIT / (Total Assets - Current Liabilities)
    """
    try:
        # Get the last 3 years of data
        years = financials.columns[:3]
        ebit = financials.loc['EBIT', years].sum()
        
        total_assets = balance_sheet.loc['Total Assets', years].sum()
        current_liabilities = balance_sheet.loc['Current Liabilities', years].sum()
        
        capital_employed = total_assets - current_liabilities
        
        if capital_employed == 0:
            return 0.0

        roce = (ebit / capital_employed) * 100
        return roce
    except (KeyError, IndexError):
        return None

def get_3yr_cumulative_fcf(cash_flow):
    """
    Calculates 3-year cumulative Free Cash Flow.
    FCF = Operating Cash Flow - Capital Expenditure
    """
    try:
        years = cash_flow.columns[:3]
        op_cash_flow = cash_flow.loc['Operating Cash Flow', years].sum()
        cap_ex = cash_flow.loc['Capital Expenditure', years].sum() # Capex is usually negative
        
        fcf_cumulative = op_cash_flow + cap_ex
        return fcf_cumulative / 1_00_00_000 # Convert to Crores
    except (KeyError, IndexError):
        return None

def check_layer1(financials, balance_sheet, cash_flow, config: dict) -> tuple[bool, dict]:
    """
    Check for Layer 1: Quality (The Moat).
    - ROCE (3yr avg) > 15%
    - FCF (3yr cumulative) > 0
    """
    try:
        if financials.empty or balance_sheet.empty or cash_flow.empty:
             return False, {"reason": "missing_financial_data"}

        roce_avg = get_3yr_avg_roce(financials, balance_sheet)
        fcf_cumulative = get_3yr_cumulative_fcf(cash_flow)
        
        if roce_avg is None or fcf_cumulative is None:
            return False, {"reason": "missing_data_for_l1_calc", "metrics": {"roce": roce_avg, "fcf": fcf_cumulative}}

        passes = (
            roce_avg > config['layer1_quality']['roce_min_pct'] and
            fcf_cumulative > 0
        )
        
        return passes, {
            "l1_roce_3yr": round(roce_avg, 2),
            "l1_fcf_cumulative": round(fcf_cumulative, 2)
        }
    except Exception as e:
        return False, {"reason": f"error_in_l1: {e}"}
