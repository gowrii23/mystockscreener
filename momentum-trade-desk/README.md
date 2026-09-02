# Momentum Trade Desk

Daily NSE momentum scanner with **Nifty OTM CE (Call Option)** signals and a browser-based trade scoring desk.

Automatically fetches NSE bhavcopy data via GitHub Actions, ranks momentum stocks using the Minervini trend template + O'Neil relative strength, and recommends out-of-the-money Nifty call strikes when index momentum is bullish.

## What it does

1. **`fetch_bhavcopy.py`** — Downloads NSE's free daily bhavcopy (end-of-day prices for all listed stocks)
2. **`scan_momentum.py`** — Scans bhavcopy history for top momentum stocks and checks Nifty 50 momentum for OTM CE entry ideas
3. **`scan_nifty_conviction.py`** — Nifty short-vol conviction checklist (paper mode, ₹10L capital model)
4. **`validate_trade.py`** — Validates yesterday's `QUALIFIED_SETUP` against today's Nifty session; logs PROFIT / LOSS / NEUTRAL
5. **`index.html`** — Browser trade desk with momentum scan + conviction panel + trade log

## Predict → validate → log (trade logger)

| Step | When | What happens |
|------|------|--------------|
| **Predict** | Pre-market or EOD when `QUALIFIED_SETUP` | Ladder saved to `data/predictions/YYYY-MM-DD.json` |
| **Validate** | Next trading day EOD (before new scans) | `validate_trade.py` fetches Nifty O/H/L/C, estimates P&L, writes outcome |
| **Log** | After validation | Row appended to `data/trade_log.csv` + `output/trade_log.json` |

Outcomes use a ±₹1,500 neutral band. P&L uses per-leg target premiums (₹40/leg), intraday breach detection (ITM at day low/high), and range-adjusted theta when all legs stay OTM at close.

Predictions are saved per run kind (`YYYY-MM-DD_premarket.json` / `YYYY-MM-DD_eod.json`). EOD signals validate the next trading day; pre-market signals validate the same day at EOD. Trade logger is blocked when momentum regime is BEARISH (conflicts with short CE wing).

## Scheduled jobs (GitHub Actions — free on public repos)

| Workflow | Schedule | What it does |
|----------|----------|--------------|
| **Daily Momentum Scan** | Mon–Fri ~7:00 PM IST | Validate prior prediction → fetch bhavcopy → momentum + conviction scans → deploy Pages |
| **Pre-Market Conviction Check** | Mon–Fri ~8:45 AM IST | Run conviction checklist → save prediction if qualified → deploy Pages |

Both are **paper mode only** — they propose setups, never place broker orders.

## Quick start (local)

```bash
pip install -r requirements.txt
python3 fetch_bhavcopy.py --backfill 200   # ~3 min, builds SMA/RS history
python3 scan_momentum.py                   # writes output/latest_scan.json
python3 scan_nifty_conviction.py           # writes output/nifty_setup.json
python3 validate_trade.py                  # validate prior QUALIFIED_SETUP (run EOD next day)
python3 -m http.server 8080                # open http://localhost:8080
```

## GitHub deployment

### 1. Create a public repo

On GitHub, create a new **public** repository named `momentum-trade-desk` (empty, no README).

### 2. Push this code

```bash
cd momentum-trade-desk
git init
git add .
git commit -m "Initial commit: momentum scanner + Nifty OTM CE signals"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/momentum-trade-desk.git
git push -u origin main
```

### 3. Enable GitHub Pages

1. Go to **Settings → Pages**
2. Under **Build and deployment**, set Source to **GitHub Actions**
3. The `daily-scan.yml` workflow deploys the site automatically

### 4. Run the first scan

Go to **Actions → Daily Momentum Scan → Run workflow**.  
On first run, set `backfill_days` to `200` to build price history, then run again with `0` for daily updates.

The workflow runs automatically **Mon–Fri at ~7:00 PM IST** after NSE publishes bhavcopy.

## Nifty OTM CE logic

When Nifty passes the momentum trend template:

- Price > SMA50 > SMA150 > SMA200
- Within 25% of 52-week high
- At least 30% above 52-week low
- 200 SMA trending up

The scanner suggests an **OTM CE strike** ~150 points above ATM (rounded to nearest 50). Example: Nifty at 24,350 → suggests `NIFTY 24550 CE`.

| Signal | Meaning |
|--------|---------|
| **BUY** | Full momentum template confirmed — OTM CE candidate |
| **WATCH** | Bullish regime but template not fully confirmed |
| **SKIP** | Bearish regime (below 200 SMA) — avoid new long CE |

See `docs/momentum-trading-rules.md` for the full rule set (position sizing, IV checks, expiry preferences).

## Output files

| File | Description |
|------|-------------|
| `output/latest_scan.json` | Full momentum scan (Nifty + top stocks) |
| `output/nifty_setup.json` | Latest conviction check + proposed ladder |
| `output/trade_log.json` | Validated trades + pending predictions (for UI) |
| `data/trade_log.csv` | Append-only validated trade outcomes |
| `data/predictions/` | One JSON per day when `QUALIFIED_SETUP` (awaiting next-day validation) |
| `data/conviction_results.csv` | Append-only audit log (one row per run) |
| `data/blackout_calendar.csv` | Event blackout dates — edit to add RBI/Budget/Fed |
| `output/latest_scan.csv` | Top momentum stocks as CSV |
| `bhavcopy_data/` | Cached daily NSE bhavcopy (gitignored locally, cached in Actions) |

See `docs/nifty-options-business-plan.md` for the full conviction framework (₹10L capital, kill-switches, discipline log).

## Disclaimer

Scoring tool only — **not order execution**. Backtest and paper-trade before live use. Options involve significant risk; OTM calls are high-variance bets — size accordingly.
