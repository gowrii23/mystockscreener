import pandas as pd
from data_fetcher import fetch_financials, fetch_balance_sheet, fetch_info

def get_piotroski_score(financials, balance_sheet, cash_flow, info):
    """
    Calculates Piotroski F-Score.
    Not all metrics are available via yfinance, so this is a best-effort implementation.
    """
    score = 0
    try:
        # Profitability (4 points)
        # 1. Positive ROA
        roa = financials.loc['Net Income', financials.columns[0]] / balance_sheet.loc['Total Assets', balance_sheet.columns[0]]
        if roa > 0: score += 1
        # 2. Positive operating cash flow
        if cash_flow.loc['Operating Cash Flow', cash_flow.columns[0]] > 0: score += 1
        # 3. Increasing ROA yoy
        roa_prev = financials.loc['Net Income', financials.columns[1]] / balance_sheet.loc['Total Assets', balance_sheet.columns[1]]
        if roa > roa_prev: score += 1
        # 4. Accruals: operating CF > Net Income (not ROA as in plan, which is a typo)
        if cash_flow.loc['Operating Cash Flow', cash_flow.columns[0]] > financials.loc['Net Income', financials.columns[0]]: score += 1
        
        # Leverage/Liquidity (3 points)
        # 5. Decreasing long-term debt ratio
        # Not easily calculable with yfinance data, so we'll check debtToEquity
        debt_equity = info.get('debtToEquity', 1)
        if debt_equity < 1: score += 1 # Simplified
        # 6. Improving current ratio
        current_ratio = info.get('currentRatio', 0)
        # Cannot easily get historical current ratio, so this is a simplification
        if current_ratio > 1: score += 1
        # 7. No new share dilution
        # Cannot easily check this without historical shares outstanding
        
        # Operating Efficiency (2 points)
        # 8. Improving gross margin
        # Not easily available
        # 9. Improving asset turnover
        # Not easily available

        return score
    except (KeyError, IndexError):
        return 0

def check_layer2(info, financials, balance_sheet, cash_flow, config: dict) -> tuple[bool, dict]:
    """
    Check for Layer 2: Safety (The Floor).
    - Debt/Equity < 1.0
    - Promoter Pledging < 10% (Skipped)
    - Piotroski F-Score >= 7
    - Interest Coverage > 3
    """
    try:
        if not info or financials.empty or balance_sheet.empty or cash_flow.empty:
            return False, {"reason": "missing_data_for_l2"}

        # Debt/Equity
        debt_equity = info.get('debtToEquity', 100) / 100 # yfinance gives it as percentage
        if debt_equity is None: debt_equity = 100

        # Promoter Pledging - SKIPPED as data is not available
        promoter_pledging = 0.0

        # Piotroski F-Score
        piotroski = get_piotroski_score(financials, balance_sheet, cash_flow, info)

        # Interest Coverage
        interest_coverage = info.get('interestCoverage') # Not always available
        if interest_coverage is None:
            try:
                ebit = financials.loc['EBIT', financials.columns[0]]
                interest_expense = financials.loc['Interest Expense', financials.columns[0]]
                if interest_expense == 0:
                    interest_coverage = 100 # high number
                else:
                    interest_coverage = abs(ebit / interest_expense)
            except (KeyError, IndexError):
                interest_coverage = 0
        if interest_coverage is None: interest_coverage = 0

        passes = (
            debt_equity < config['layer2_safety']['debt_equity_max'] and
            promoter_pledging < config['layer2_safety']['promoter_pledging_max_pct'] and
            piotroski >= config['layer2_safety']['piotroski_min'] and
            interest_coverage > config['layer2_safety']['interest_coverage_min']
        )

        return passes, {
            "l2_debt_equity": round(debt_equity, 2),
            "l2_pledging_pct": promoter_pledging,
            "l2_piotroski": piotroski,
            "l2_interest_coverage": round(interest_coverage, 2)
        }

    except Exception as e:
        return False, {"reason": f"error_in_l2: {e}"}
