import pandas as pd
import yaml
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent))
from engine_a.audit_logger import audit_log
from regime_filter import get_market_regime
from freshness_check import check_data_freshness
from layer5_momentum import check_layer5

def run_engine_b():
    """
    Runs the momentum and regime scanner (Engine B).
    """
    # 1. Load Config
    try:
        with open("engine_a/config.yaml", 'r') as f:
            config = yaml.safe_load(f)
    except FileNotFoundError:
        print("Error: config.yaml not found in engine_a/ directory.")
        return

    # 2. Check Market Regime
    print("Checking market regime...")
    regime = get_market_regime()
    if regime != "BULLISH":
        print(f"Market regime is '{regime}'. Engine B will not run.")
        audit_log("MARKET", "HALT", f"Regime is {regime}")
        return
    print(f"Market regime is '{regime}'.")

    # 3. Check Data Freshness
    qualified_universe_path = "engine_a/output/qualified_universe.csv"
    print("Checking data freshness...")
    is_fresh, message = check_data_freshness(qualified_universe_path, config['data_quality']['staleness_days'])
    if not is_fresh:
        print(message)
        audit_log("DATA", "HALT", message)
        return
    print(message)

    # 4. Read Qualified Tickers
    try:
        qualified_df = pd.read_csv(qualified_universe_path)
        qualified_tickers = qualified_df['ticker'].tolist()
        print(f"Found {len(qualified_tickers)} qualified tickers from Engine A.")
    except (FileNotFoundError, KeyError):
        print("Error: Could not read qualified tickers from CSV.")
        return
    
    # 5. Run Momentum Check
    ranked_candidates = []
    for ticker in qualified_tickers:
        print(f"--- Scanning {ticker} for momentum ---")
        passes, metrics = check_layer5(ticker, config)
        if passes:
            print(f"+++ {ticker} PASSED MOMENTUM CHECK +++")
            ranked_candidates.append({
                "ticker": ticker,
                **metrics
            })
            audit_log(ticker, "PASS_L5", "Momentum check passed", metrics)
        else:
            audit_log(ticker, "FAIL_L5", metrics.get("reason", "Momentum gate failed"), metrics)
            
    # 6. Save Ranked Candidates
    if ranked_candidates:
        df = pd.DataFrame(ranked_candidates)
        output_path = "engine_b/output/ranked_candidates.csv"
        df.to_csv(output_path, index=False)
        print(f"\nEngine B complete. {len(df)} stocks passed momentum check.")
        print(f"Results saved to {output_path}")
    else:
        print("\nEngine B complete. No stocks passed momentum check.")


if __name__ == "__main__":
    run_engine_b()
