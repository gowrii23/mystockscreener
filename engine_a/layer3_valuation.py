from data_fetcher import fetch_info, fetch_cash_flow
from dataclasses import dataclass
import numpy as np

@dataclass
class DCFResult:
    bear: float
    base: float
    bull: float
    margin_of_safety_pct: float
    verdict: str
    outlier_reason: str | None = None

def get_fcf_growth_rate(cash_flow, years=3):
    """
    Calculates the Free Cash Flow (FCF) Compound Annual Growth Rate (CAGR).
    """
    try:
        fcf = cash_flow.loc['Operating Cash Flow'] + cash_flow.loc['Capital Expenditure']
        # Ensure we have enough data points
        if len(fcf) < years:
            return 0.0
        
        start_val = fcf[years-1]
        end_val = fcf[0]

        # Handle cases where start or end values are not positive
        if start_val <= 0 or end_val <= 0:
            return 0.0

        cagr = (end_val / start_val) ** (1/years) - 1
        return cagr
    except (KeyError, IndexError):
        return 0.0

def calculate_dcf(
    current_fcf: float,
    fcf_growth_rate: float,
    current_price: float,
    shares_outstanding: float,
    config: dict
) -> DCFResult:
    cfg = config['layer3_valuation']
    tg = cfg['terminal_growth_rate']
    rf = cfg['risk_free_rate']
    years = 5

    def _dcf(growth: float, wacc: float) -> float:
        pv_fcf = 0.0
        cf = current_fcf
        for i in range(1, years + 1):
            cf *= (1 + growth)
            pv_fcf += cf / (1 + wacc) ** i
        
        terminal_value = cf * (1 + tg) / (wacc - tg)
        pv_terminal_value = terminal_value / (1 + wacc) ** years
        
        total_pv = pv_fcf + pv_terminal_value
        intrinsic_value_per_share = total_pv / shares_outstanding
        return intrinsic_value_per_share

    wacc_base = rf + 0.04  # 4% equity risk premium as in plan
    bear = _dcf(fcf_growth_rate * cfg['dcf_bear_growth_multiplier'], wacc_base + cfg['dcf_bear_wacc_addition'])
    base = _dcf(fcf_growth_rate, wacc_base)
    bull = _dcf(fcf_growth_rate * cfg['dcf_bull_growth_multiplier'], wacc_base - cfg['dcf_bull_wacc_reduction'])

    # Sanity checks
    if base > current_price * cfg['sanity_max_multiple']:
        return DCFResult(bear, base, bull, 0, "OUTLIER", "DCF_OUTLIER_HIGH")
    if base < current_price * cfg['sanity_min_multiple']:
        return DCFResult(bear, base, bull, 0, "OUTLIER", "DCF_OUTLIER_LOW")

    mos = ((base - current_price) / base) * 100 if base > 0 else 0
    verdict = "PASS" if mos >= cfg['margin_of_safety_min_pct'] else "FAIL"
    return DCFResult(bear, base, bull, round(mos, 2), verdict)

def check_ev_ebitda(info: dict, config: dict) -> dict:
    ev = info.get('enterpriseValue')
    ebitda = info.get('ebitda')
    
    if ev is None or ebitda is None or ebitda == 0:
        return {"ev_ebitda": float('inf'), "flag": True, "note": "EV/EBITDA data not available"}
        
    ratio = ev / ebitda
    threshold = config['layer3_valuation']['ev_ebitda_max']
    return {
        "ev_ebitda": round(ratio, 2),
        "flag": ratio > threshold,
        "note": f"EV/EBITDA {ratio:.1f}x — {'above' if ratio > threshold else 'below'} {threshold}x threshold"
    }

def check_layer3(info, cash_flow, config: dict) -> tuple[bool, dict]:
    """
    Check for Layer 3: Valuation (DCF Engine).
    - Margin of Safety > 20%
    - EV/EBITDA cross-check
    """
    try:
        if not info or cash_flow.empty:
            return False, {"reason": "missing_data_for_l3"}

        current_price = info.get('regularMarketPrice')
        shares_outstanding = info.get('sharesOutstanding')
        current_fcf = cash_flow.loc['Operating Cash Flow', cash_flow.columns[0]] + cash_flow.loc['Capital Expenditure', cash_flow.columns[0]]
        
        if current_price is None or shares_outstanding is None or current_fcf is None:
             return False, {"reason": "missing_core_data_for_dcf"}

        fcf_growth_rate = get_fcf_growth_rate(cash_flow)
        
        dcf_result = calculate_dcf(current_fcf, fcf_growth_rate, current_price, shares_outstanding, config)

        ev_ebitda_check = check_ev_ebitda(info, config)

        passes = dcf_result.verdict == "PASS" and not ev_ebitda_check['flag']
        
        return passes, {
            "l3_dcf_bear": round(dcf_result.bear, 2),
            "l3_dcf_base": round(dcf_result.base, 2),
            "l3_dcf_bull": round(dcf_result.bull, 2),
            "l3_margin_of_safety": dcf_result.margin_of_safety_pct,
            "l3_ev_ebitda": ev_ebitda_check['ev_ebitda'],
            "l3_dcf_verdict": dcf_result.verdict,
            "l3_ev_ebitda_flag": ev_ebitda_check['flag']
        }

    except Exception as e:
        return False, {"reason": f"error_in_l3: {e}"}
