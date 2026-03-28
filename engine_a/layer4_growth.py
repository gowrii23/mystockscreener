from data_fetcher import fetch_financials

def get_cagr(series, years=3):
    """
    Calculates Compound Annual Growth Rate for a given pandas series.
    """
    try:
        start_val = series[years-1]
        end_val = series[0]

        if start_val <= 0: # Can't calculate growth from non-positive number
            return 0.0

        cagr = (end_val / start_val) ** (1/years) - 1
        return cagr * 100
    except (KeyError, IndexError):
        return 0.0

def get_opm_trend(financials, config):
    """
    Checks if the Operating Profit Margin is Stable or Expanding.
    OPM = Operating Income / Total Revenue
    """
    try:
        op_income = financials.loc['Operating Income']
        revenue = financials.loc['Total Revenue']
        opm = (op_income / revenue) * 100
        
        # Check for contraction
        contraction = opm[0] - opm[2] # Year 1 vs Year 3
        if contraction < -config['layer4_growth']['opm_max_contraction_pct']:
            return "contracting"
        elif abs(contraction) <= config['layer4_growth']['opm_max_contraction_pct']:
            return "stable"
        else:
            return "expanding"
            
    except (KeyError, IndexError):
        return "unknown"


def check_layer4(financials, config: dict) -> tuple[bool, dict]:
    """
    Check for Layer 4: Growth (The Engine).
    - EPS CAGR (3yr) > 12%
    - Revenue CAGR (3yr) > 10%
    - OPM trend Stable or Expanding
    """
    try:
        if financials.empty or len(financials.columns) < 3:
            return False, {"reason": "insufficient_financial_data_for_l4"}

        # EPS CAGR
        eps = financials.loc['Basic EPS']
        eps_cagr = get_cagr(eps)

        # Revenue CAGR
        revenue = financials.loc['Total Revenue']
        revenue_cagr = get_cagr(revenue)
        
        # OPM Trend
        opm_trend = get_opm_trend(financials, config)

        passes = (
            eps_cagr > config['layer4_growth']['eps_cagr_min_pct'] and
            revenue_cagr > config['layer4_growth']['revenue_cagr_min_pct'] and
            opm_trend in ["stable", "expanding"]
        )

        return passes, {
            "l4_eps_cagr_3yr": round(eps_cagr, 2),
            "l4_revenue_cagr_3yr": round(revenue_cagr, 2),
            "l4_opm_trend": opm_trend
        }

    except Exception as e:
        return False, {"reason": f"error_in_l4: {e}"}
