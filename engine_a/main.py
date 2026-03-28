import pandas as pd
import yaml
from datetime import datetime
import data_fetcher
from layer1_quality import check_layer1
from layer2_safety import check_layer2
from layer3_valuation import check_layer3
from layer4_growth import check_layer4
from audit_logger import audit_log

def run_engine_a():
    """
    Runs the full fundamental analysis pipeline (Engine A).
    """
    with open("engine_a/config.yaml", 'r') as f:
        config = yaml.safe_load(f)
    
    try:
        tickers_df = pd.read_csv("data/nifty500.csv")
        tickers = tickers_df['Symbol'].tolist()
    except FileNotFoundError:
        print("Error: nifty500.csv not found in data/ directory.")
        return

    results = []
    
    # Let's run for a subset of tickers for now to test
    for ticker in tickers[:20]:
        print(f"--- Processing {ticker} ---")

        # 1. Fetch all data for the ticker once
        info = data_fetcher.fetch_info(ticker)
        if not info:
            audit_log(ticker, "SKIP", "Could not fetch stock info.")
            continue
        
        financials = data_fetcher.fetch_financials(ticker)
        balance_sheet = data_fetcher.fetch_balance_sheet(ticker)
        cash_flow = data_fetcher.fetch_cash_flow(ticker)

        # 2. Run Layer 1 Check
        p1, m1 = check_layer1(financials, balance_sheet, cash_flow, config)
        if not p1:
            audit_log(ticker, "FAIL_L1", m1.get("reason", "Quality gate failed"), m1)
            continue

        # 3. Run Layer 2 Check
        p2, m2 = check_layer2(info, financials, balance_sheet, cash_flow, config)
        if not p2:
            audit_log(ticker, "FAIL_L2", m2.get("reason", "Safety gate failed"), m2)
            continue

        # 4. Run Layer 3 Check
        p3, m3 = check_layer3(info, cash_flow, config)
        if not p3:
            audit_log(ticker, "FAIL_L3", m3.get("reason", "Valuation gate failed"), m3)
            continue

        # 5. Run Layer 4 Check
        p4, m4 = check_layer4(financials, config)
        if not p4:
            audit_log(ticker, "FAIL_L4", m4.get("reason", "Growth gate failed"), m4)
            continue

        # 6. If all layers pass, collect the results
        print(f"+++ {ticker} PASSED ALL LAYERS +++")
        all_metrics = {
            "ticker": ticker,
            "company_name": info.get('longName', ''),
            **m1, **m2, **m3, **m4
        }
        results.append(all_metrics)
        audit_log(ticker, "PASS", "All 4 layers passed", all_metrics)

    # 7. Create and save the final DataFrame
    if results:
        df = pd.DataFrame(results)
        df['last_updated'] = datetime.now().isoformat()
        
        # Reorder columns to match the plan
        cols_order = [
            'ticker', 'company_name', 'last_updated',
            'l1_roce_3yr', 'l1_fcf_cumulative',
            'l2_debt_equity', 'l2_pledging_pct', 'l2_piotroski', 'l2_interest_coverage',
            'l3_dcf_bear', 'l3_dcf_base', 'l3_dcf_bull', 'l3_margin_of_safety', 'l3_ev_ebitda',
            'l4_eps_cagr_3yr', 'l4_opm_trend', 'l4_revenue_cagr_3yr'
        ]
        # Add any missing columns that might not have been generated (e.g. if no stock passed)
        for col in cols_order:
            if col not in df.columns:
                df[col] = None
        
        df = df[cols_order]
        
        output_path = "engine_a/output/qualified_universe.csv"
        df.to_csv(output_path, index=False)
        print(f"\nEngine A complete. {len(df)} stocks qualified.")
        print(f"Results saved to {output_path}")
    else:
        print("\nEngine A complete. No stocks qualified.")

if __name__ == "__main__":
    # Before running, we need to install dependencies
    # pip install yfinance pandas pyyaml
    run_engine_a()
