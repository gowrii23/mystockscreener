# ◈ TradeFilter

This project is a multi-layered stock filtering and analysis tool designed to identify investment opportunities based on a series of fundamental and technical checks. It is composed of two main data processing engines and a web-based dashboard for visualization.

## Momentum Trade Desk (live)

**Web app:** https://gowrii23.github.io/mystockscreener/

Nifty momentum scan + conviction-based short-vol checklist (paper mode). Auto-updated via GitHub Actions cron (free on public repos).

```
momentum-trade-desk/
├── index.html              # Trade desk UI
├── scan_momentum.py        # EOD momentum + OTM CE signals
├── scan_nifty_conviction.py # Pre-market / EOD conviction check
├── data/conviction_results.csv  # Append-only audit log
└── output/latest_scan.json, nifty_setup.json
```

## How it Works

The workflow is divided into three main stages:

1.  **Engine A (Fundamental Analysis):** This engine scans a universe of stocks (e.g., Nifty 500) and applies a series of fundamental filters related to quality, safety, valuation, and growth. Stocks that pass all these layers are saved as the "Qualified Universe". This engine fetches fresh data from the internet.
2.  **Engine B (Momentum Scan):** This engine takes the "Qualified Universe" from Engine A and applies further technical checks. It first determines the overall market regime (e.g., bullish, bearish). If the regime is favorable, it then scans the qualified stocks for momentum signals.
3.  **Dashboard:** A Streamlit web application that provides a view of the outputs from both engines, including the list of qualified stocks, the final ranked candidates, and an audit log of the entire filtering process.

## Directory Structure

```
├───dashboard.py                # Main Streamlit dashboard application
├───engine_a/
│   ├───main.py                 # Main script for Engine A (Fundamental Analysis)
│   ├───data_fetcher.py         # Fetches financial data from yfinance
│   ├───layer1_quality.py       # Quality filter logic
│   ├───layer2_safety.py        # Safety filter logic
│   ├───layer3_valuation.py     # Valuation filter logic
│   ├───layer4_growth.py        # Growth filter logic
│   ├───config.yaml             # Configuration for Engine A's filter parameters
│   └───output/
│       └───qualified_universe.csv # Output of Engine A
├───engine_b/
│   ├───main.py                 # Main script for Engine B (Momentum Scan)
│   ├───regime_filter.py        # Determines the current market regime
│   ├───freshness_check.py      # Checks if the data from Engine A is up-to-date
│   ├───layer5_momentum.py      # Momentum filter logic
│   └───output/
│       └───ranked_candidates.csv # Output of Engine B
├───data/
│   └───nifty500.csv            # Input list of stocks to be analyzed
└───logs/
    └───audit_log.jsonl         # Detailed log of all operations
```

## Setup

Before running the application, you need to install the required Python libraries.

```bash
pip install streamlit pandas pyyaml yfinance matplotlib
```

## Usage

Follow these steps to run the complete analysis and view the dashboard.

### Step 1: Run Engine A (Fundamental Analysis)

This step fetches the latest financial data and filters stocks based on fundamental criteria. This may take a significant amount of time as it needs to fetch data for many stocks.

Open your terminal and run the following command:

```bash
python engine_a/main.py
```

This will create or update the `engine_a/output/qualified_universe.csv` file.

### Step 2: Run Engine B (Momentum Scan)

Once Engine A has successfully run, you can run Engine B. This engine checks the market regime and then looks for momentum signals in the fundamentally strong stocks identified by Engine A.

```bash
python engine_b/main.py
```

This will create or update the `engine_b/output/ranked_candidates.csv` file. Note that this engine may not produce any output if the market regime is not "BULLISH" or if no stocks pass the momentum check.

### Step 3: Launch the Dashboard

After running the engines, you can launch the web dashboard to view the results.

```bash
streamlit run dashboard.py
```

Now, open your web browser and navigate to the local URL provided by Streamlit (usually `http://localhost:8501`).

## Data Refresh Schedule

The data for this tool is sourced from the internet and goes stale over time.

*   **Engine A:** You should run Engine A periodically to ensure the fundamental data is fresh. Based on the `freshness_check.py` script, the data from Engine A is considered stale after **7 days**. It is recommended to run **Engine A weekly**.
*   **Engine B:** You can run Engine B more frequently, such as **daily**, to check for new momentum signals, especially after running Engine A.

## Configuration

The filtering criteria and thresholds for the layers in Engine A can be adjusted in the `engine_a/config.yaml` file.
