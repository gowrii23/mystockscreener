# Robust Layered Filter Trading Strategy — V2.0
## Personal Finance App · Complete Development Plan

---

## Table of Contents

1. [Vision & Guiding Principles](#1-vision--guiding-principles)
2. [System Architecture](#2-system-architecture)
3. [The 5-Layer Filter Pipeline](#3-the-5-layer-filter-pipeline)
4. [DCF Valuation Engine](#4-dcf-valuation-engine)
5. [Data Integrity & Health Checks](#5-data-integrity--health-checks)
6. [Risk Controls (Critical Additions)](#6-risk-controls-critical-additions)
7. [UI Wireframe & Dashboard Design](#7-ui-wireframe--dashboard-design)
8. [Development Roadmap](#8-development-roadmap)
9. [Phase-by-Phase Dev Instructions](#9-phase-by-phase-dev-instructions)
10. [Tech Stack & Dependencies](#10-tech-stack--dependencies)
11. [Testing & Validation Checklist](#11-testing--validation-checklist)
12. [Appendix: Key Formulas](#12-appendix-key-formulas)

---

## 1. Vision & Guiding Principles

This is a **personal finance tool**, not a trading bot. Its job is to surface high-quality investment candidates from the Nifty 500 universe using a disciplined, multi-layered filter — and to keep you from making impulsive decisions. Every design decision should serve that goal.

**Core Principles:**

- **Data over gut** — every buy/skip decision is logged with the exact metrics that drove it.
- **Conservative by default** — when in doubt, the system skips, not buys. Missing a good stock is less costly than owning a bad one.
- **Transparent failures** — the app must surface *why* a stock was filtered out, not just that it was.
- **Separation of concerns** — heavy fundamental analysis runs weekly (Engine A); fast technical scanning runs daily (Engine B). Never mix them.
- **No magic numbers** — all thresholds are visible, documented, and adjustable in a single config file.

---

## 2. System Architecture

### Two-Engine Design

```
┌─────────────────────────────────────────────────────┐
│                    WEEKLY BATCH                     │
│                    (Engine A)                       │
│                                                     │
│  Nifty 500 Tickers → Layer 1→2→3→4 Filter          │
│  Output: qualified_universe.csv                     │
│  Schedule: Sunday 9 PM IST (cron)                   │
└─────────────────────────┬───────────────────────────┘
                          │  qualified_universe.csv
                          │  (with last_updated timestamp)
                          ▼
┌─────────────────────────────────────────────────────┐
│                  REAL-TIME SCANNER                  │
│                    (Engine B)                       │
│                                                     │
│  Read CSV → Freshness Check → Layer 5 Momentum      │
│  Output: ranked_candidates.csv                      │
│  Schedule: Runs 9:30 AM–3:30 PM IST on trading days │
└─────────────────────────┬───────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────┐
│               STREAMLIT DASHBOARD                   │
│                                                     │
│  Qualified Universe View | Why Buy Panel            │
│  DCF Scenario Chart | Portfolio Tracker             │
│  Audit Log | Risk Alerts                            │
└─────────────────────────────────────────────────────┘
```

### State Management

The `qualified_universe.csv` file is the contract between the two engines. It must contain:

| Column | Type | Description |
|--------|------|-------------|
| ticker | str | NSE symbol |
| company_name | str | Full name |
| last_updated | datetime | Batch run timestamp |
| l1_roce_3yr | float | 3-year average ROCE % |
| l1_fcf_cumulative | float | 3-year cumulative FCF (Cr) |
| l2_debt_equity | float | D/E ratio |
| l2_pledging_pct | float | Promoter pledging % |
| l2_piotroski | int | F-Score (0–9) |
| l2_interest_coverage | float | Interest coverage ratio |
| l3_dcf_bear | float | Bear-case intrinsic value |
| l3_dcf_base | float | Base-case intrinsic value |
| l3_dcf_bull | float | Bull-case intrinsic value |
| l3_margin_of_safety | float | MoS % vs current price |
| l3_ev_ebitda | float | EV/EBITDA cross-check |
| l4_eps_cagr_3yr | float | 3-year EPS CAGR % |
| l4_opm_trend | str | expanding / stable / contracting |
| l4_revenue_cagr_3yr | float | 3-year revenue CAGR % |
| quality_score | float | Composite 0–100 score |
| pass_layers | str | Comma-separated passed layers |

### Circuit Breaker Logic

Engine B must check freshness **before** processing any ticker:

```python
from datetime import datetime, timedelta

def check_data_freshness(csv_path: str, max_age_days: int = 7):
    df = pd.read_csv(csv_path)
    last_updated = pd.to_datetime(df['last_updated'].iloc[0])
    age = datetime.now() - last_updated
    if age > timedelta(days=max_age_days):
        raise StaleDataError(
            f"qualified_universe.csv is {age.days} days old. "
            f"Run Engine A before scanning."
        )
```

---

## 3. The 5-Layer Filter Pipeline

All thresholds live in `config.yaml`. Never hardcode them in logic files.

### config.yaml (template)

```yaml
universe:
  index: "nifty500"
  min_market_cap_cr: 500

layer1_quality:
  roce_min_pct: 15.0
  roce_years: 3
  fcf_require_positive_cumulative: true
  fcf_years: 3

layer2_safety:
  debt_equity_max: 1.0
  debt_equity_max_high_risk_sectors: 0.5
  high_risk_sectors: ["realestate", "infrastructure", "nbfc"]
  promoter_pledging_max_pct: 10.0
  piotroski_min: 7
  interest_coverage_min: 3.0

layer3_valuation:
  margin_of_safety_min_pct: 20.0
  terminal_growth_rate: 0.03
  risk_free_rate: 0.075
  dcf_bear_growth_multiplier: 0.6
  dcf_bull_growth_multiplier: 1.4
  dcf_bull_wacc_reduction: 0.01
  dcf_bear_wacc_addition: 0.02
  sanity_max_multiple: 3.0   # Flag if DCF > 300% of current price
  sanity_min_multiple: 0.1   # Flag if DCF < 10% of current price
  ev_ebitda_max: 15.0

layer4_growth:
  eps_cagr_min_pct: 12.0
  eps_cagr_years: 3
  revenue_cagr_min_pct: 10.0
  opm_max_contraction_pct: 2.0   # Allow max 2% OPM decline

layer5_momentum:
  ema_short: 20
  ema_long: 50
  ema_trend_filter: 200
  rsi_min: 50
  rsi_max_entry: 70            # Avoid overbought entries
  rsi_sweet_spot_max: 65
  volume_ratio_min: 1.5
  high_52w_buffer_pct: 5.0    # Avoid stocks within 5% of 52w high

risk_controls:
  max_position_pct: 5.0
  max_sector_pct: 30.0
  stop_loss_pct: 15.0
  trailing_stop_pct: 20.0

data_quality:
  max_null_core_metrics: 2
  staleness_days: 7
```

---

### Layer 1 — Quality (The Moat)

**Purpose:** Identify companies with genuine competitive advantages.

| Metric | Threshold | Rationale |
|--------|-----------|-----------|
| ROCE (3yr avg) | > 15% | Harder to manipulate than ROE; signals real capital efficiency |
| FCF (3yr cumulative) | Positive | Real cash, not accounting profit |

**Implementation note:** If FCF is negative in 1 of 3 years, flag it but don't auto-reject. Require cumulative FCF to be net positive over the 3-year period.

**Code skeleton:**

```python
def check_layer1(ticker_data: dict, config: dict) -> tuple[bool, dict]:
    roce_avg = ticker_data.get('roce_3yr_avg')
    fcf_cumulative = ticker_data.get('fcf_3yr_cumulative')

    if roce_avg is None or fcf_cumulative is None:
        return False, {"reason": "missing_data", "metrics": {"roce": roce_avg}}

    passes = (
        roce_avg > config['layer1_quality']['roce_min_pct'] and
        fcf_cumulative > 0
    )
    return passes, {
        "roce_3yr_avg": round(roce_avg, 2),
        "fcf_cumulative": round(fcf_cumulative, 2),
        "fcf_negative_years": ticker_data.get('fcf_negative_years', 0)
    }
```

---

### Layer 2 — Safety (The Floor)

**Purpose:** Eliminate companies with structural financial risk.

| Metric | Threshold | Rationale |
|--------|-----------|-----------|
| Debt/Equity | < 1.0 (< 0.5 for high-risk sectors) | Solvency under stress |
| Promoter Pledging | < 10% | Forced-selling risk in downturns |
| Piotroski F-Score | ≥ 7 | Detects accounting red flags |
| Interest Coverage | > 3× | Supplementary solvency gate (new) |

**F-Score breakdown (9 criteria):**

```
Profitability (4 points):
  + Positive ROA
  + Positive operating cash flow
  + Increasing ROA year-over-year
  + Accruals: operating CF > ROA (quality of earnings)

Leverage/Liquidity (3 points):
  + Decreasing long-term debt ratio
  + Improving current ratio
  + No new share dilution

Operating Efficiency (2 points):
  + Improving gross margin
  + Improving asset turnover
```

Score 0–2 = Weak (auto-fail regardless of other metrics)
Score 3–6 = Average (flag for manual review)
Score 7–9 = Strong (pass)

---

### Layer 3 — Valuation (DCF Engine)

**Purpose:** Ensure you're not overpaying.

**Method:** Multi-scenario DCF with EV/EBITDA cross-check.

| Parameter | Value |
|-----------|-------|
| Projection period | 5 years |
| Terminal growth rate | 3% |
| Risk-free rate | 7.5% (Indian 10yr G-Sec proxy) |
| Bear-case growth | Base × 0.6, WACC + 2% |
| Bull-case growth | Base × 1.4, WACC − 1% |
| Margin of Safety | Current price < 80% of Base IV |

**Sanity checks (mandatory):**
- If DCF result > 300% of current price → flag as `DCF_OUTLIER_HIGH`, log, skip
- If DCF result < 10% of current price → flag as `DCF_OUTLIER_LOW`, log, skip
- If EV/EBITDA > 15× → add warning even if DCF passes (secondary valuation anchor)

---

### Layer 4 — Growth (The Engine)

**Purpose:** Prevent value traps.

| Metric | Threshold | Rationale |
|--------|-----------|-----------|
| EPS CAGR (3yr) | > 12% | Earnings must grow meaningfully |
| Revenue CAGR (3yr) | > 10% | Earnings growth must be revenue-driven (new) |
| OPM trend | Stable or Expanding | Contracting margins signal competitive pressure |

**OPM rule:** Allow maximum 2% contraction over 3 years. A company with OPM going 28% → 26% is borderline acceptable. 28% → 22% is a fail.

---

### Layer 5 — Momentum (The Trigger)

**Purpose:** Fundamentals tell you *what* to buy; technicals tell you *when*.

| Signal | Condition | Note |
|--------|-----------|------|
| EMA crossover | 20 EMA above 50 EMA | Only when price > 200 EMA (trend filter — new) |
| RSI | > 50, ideally 52–65 | Avoid entries > 70 (overbought) |
| Volume | > 1.5× 20-day average | Institutional confirmation |
| 52-week high | Not within 5% of high | Avoid chasing peaks (new) |

**Market regime filter (new — critical):** If Nifty 50 is below its 200-day EMA, Engine B enters "observe only" mode. No new position signals are generated. Existing positions are monitored for stop-loss.

---

## 4. DCF Valuation Engine

### Full Function

```python
from dataclasses import dataclass

@dataclass
class DCFResult:
    bear: float
    base: float
    bull: float
    margin_of_safety_pct: float
    verdict: str  # "PASS" | "FAIL" | "OUTLIER"
    outlier_reason: str | None = None

def calculate_dcf(
    current_fcf: float,
    fcf_growth_rate: float,
    current_price: float,
    config: dict
) -> DCFResult:
    cfg = config['layer3_valuation']
    tg = cfg['terminal_growth_rate']
    rf = cfg['risk_free_rate']
    years = 5

    def _dcf(growth: float, wacc: float) -> float:
        pv = 0.0
        cf = current_fcf
        for i in range(1, years + 1):
            cf *= (1 + growth)
            pv += cf / (1 + wacc) ** i
        terminal = cf * (1 + tg) / (wacc - tg)
        pv += terminal / (1 + wacc) ** years
        return pv

    wacc_base = rf + 0.04  # 4% equity risk premium
    bear = _dcf(fcf_growth_rate * cfg['dcf_bear_growth_multiplier'],
                wacc_base + cfg['dcf_bear_wacc_addition'])
    base = _dcf(fcf_growth_rate, wacc_base)
    bull = _dcf(fcf_growth_rate * cfg['dcf_bull_growth_multiplier'],
                wacc_base - cfg['dcf_bull_wacc_reduction'])

    # Sanity checks
    if base > current_price * cfg['sanity_max_multiple']:
        return DCFResult(bear, base, bull, 0, "OUTLIER", "DCF_OUTLIER_HIGH")
    if base < current_price * cfg['sanity_min_multiple']:
        return DCFResult(bear, base, bull, 0, "OUTLIER", "DCF_OUTLIER_LOW")

    mos = (base - current_price) / base * 100
    verdict = "PASS" if mos >= cfg['margin_of_safety_min_pct'] else "FAIL"
    return DCFResult(bear, base, bull, round(mos, 2), verdict)
```

### EV/EBITDA Cross-Check

```python
def check_ev_ebitda(ev: float, ebitda: float, config: dict) -> dict:
    ratio = ev / ebitda if ebitda > 0 else float('inf')
    threshold = config['layer3_valuation']['ev_ebitda_max']
    return {
        "ev_ebitda": round(ratio, 2),
        "flag": ratio > threshold,
        "note": f"EV/EBITDA {ratio:.1f}x — {'above' if ratio > threshold else 'below'} {threshold}x threshold"
    }
```

---

## 5. Data Integrity & Health Checks

### Null Value Handler

```python
CORE_METRICS = [
    'roce_3yr_avg', 'fcf_3yr_cumulative',
    'debt_equity', 'piotroski_score',
    'dcf_base', 'eps_cagr_3yr'
]

def validate_ticker_data(ticker: str, data: dict) -> bool:
    null_count = sum(1 for m in CORE_METRICS if data.get(m) is None)
    if null_count > 2:
        audit_log(ticker, "SKIPPED", f"{null_count} core metrics are NaN")
        return False
    return True
```

### Audit Logger

Every "Pass" decision must be logged. Every "Skip" must also be logged with the reason.

```python
import json
from pathlib import Path
from datetime import datetime

def audit_log(ticker: str, decision: str, reason: str, metrics: dict = None):
    log_path = Path("logs/audit_log.jsonl")
    log_path.parent.mkdir(exist_ok=True)
    entry = {
        "timestamp": datetime.now().isoformat(),
        "ticker": ticker,
        "decision": decision,
        "reason": reason,
        "metrics": metrics or {}
    }
    with open(log_path, "a") as f:
        f.write(json.dumps(entry) + "\n")
```

### API Retry with Exponential Backoff

```python
import time
import yfinance as yf

def fetch_with_retry(ticker: str, max_retries: int = 3) -> dict | None:
    for attempt in range(max_retries):
        try:
            stock = yf.Ticker(ticker + ".NS")
            info = stock.info
            if not info or info.get('regularMarketPrice') is None:
                raise ValueError(f"Empty data for {ticker}")
            return info
        except Exception as e:
            wait = 2 ** attempt
            print(f"[{ticker}] Attempt {attempt+1} failed: {e}. Retrying in {wait}s...")
            time.sleep(wait)
    audit_log(ticker, "SKIPPED", "API_FAILURE_AFTER_RETRIES")
    return None
```

### Data Quality Checks Summary

| Check | Action | Severity |
|-------|--------|----------|
| > 2 core metrics are NaN | Skip ticker, log `NULL_DATA` | High |
| DCF result > 300% of price | Skip, log `DCF_OUTLIER_HIGH` | High |
| DCF result < 10% of price | Skip, log `DCF_OUTLIER_LOW` | High |
| CSV older than 7 days | Halt Engine B, raise `StaleDataError` | Critical |
| FCF negative in 1 of 3 years | Flag `FCF_WARNING`, don't skip | Medium |
| Promoter pledging rising trend | Flag `PLEDGING_TREND_ALERT` | Medium |
| EV/EBITDA > 15× | Add warning to output, don't skip | Low |
| yfinance API failure | Retry 3× with backoff, then skip | High |
| Corporate action not adjusted | Flag `NEEDS_ADJUSTMENT_CHECK` | Medium |

---

## 6. Risk Controls (Critical Additions)

These were **missing from V2.0** and must be implemented before deploying real capital.

### Position Sizing

```python
def calculate_position_size(
    portfolio_value: float,
    stock_price: float,
    config: dict
) -> dict:
    max_pct = config['risk_controls']['max_position_pct'] / 100
    max_amount = portfolio_value * max_pct
    max_shares = int(max_amount / stock_price)
    return {
        "max_amount_inr": max_amount,
        "max_shares": max_shares,
        "position_pct": max_pct * 100
    }
```

Rules:
- Maximum 5% of portfolio per single stock
- Maximum 30% per sector
- Apply Kelly Criterion or fixed-fraction sizing (recommended: fixed 2–5% to start)

### Exit Strategy (Define Before Entry)

Every position must have these set at the time of entry — not after:

| Exit Type | Level | Action |
|-----------|-------|--------|
| Hard stop-loss | 15% below entry price | Sell immediately, no exceptions |
| Trailing stop | 20% below all-time peak since entry | Protect gains |
| Fundamental deterioration | ROCE drops below 12% for 2 consecutive quarters | Exit on next opportunity |
| Overbought exit | RSI crosses above 75 after entry | Consider partial exit |
| Time-based review | Every quarter | Re-run all 5 layers; exit if no longer qualifies |

### Market Regime Filter

```python
def get_market_regime(nifty_data) -> str:
    ema_200 = nifty_data['Close'].ewm(span=200).mean().iloc[-1]
    current_price = nifty_data['Close'].iloc[-1]
    if current_price < ema_200:
        return "BEARISH"  # Engine B halts new signals
    return "BULLISH"
```

---

## 7. UI Wireframe & Dashboard Design

### Screen 1 — Main Dashboard

```
┌─────────────────────────────────────────────────────────────┐
│  ◈ TradeFilter        [Market: BULLISH ✓]    [Last run: Sun] │
├──────────┬──────────┬──────────┬──────────┬─────────────────┤
│ Universe │ Qualified│  Active  │Portfolio │   Alerts        │
│   500    │    47    │  Signals │   ₹2.4L  │    3 new        │
├──────────┴──────────┴──────────┴──────────┴─────────────────┤
│                                                             │
│  QUALIFIED UNIVERSE                  [Search] [Sort ▼]     │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ Ticker   Q  S  V  G  Mo  MoS%   Score   Action         │ │
│ ├─────────────────────────────────────────────────────────┤ │
│ │ BAJFIN  ✓  ✓  ✓  ✓   ✓  +31%    94     [Why Buy?] [▶] │ │
│ │ PIDLIT  ✓  ✓  ✓  ✓   ⚠  +24%    87     [Why Buy?] [▶] │ │
│ │ HDFC    ✓  ✓  ⚠  ✓   ✓   -3%    71     [Details]      │ │
│ │ RELAXO  ✓  ✗  ✓  ⚠   ✓   --    Filtered [Details]     │ │
│ └─────────────────────────────────────────────────────────┘ │
│                                                             │
│  MARKET REGIME                                             │
│  [████████████████████░░░░░] Nifty 50: ▲ 22,847           │
│  Above 200-EMA: YES — Engine B: ACTIVE                     │
└─────────────────────────────────────────────────────────────┘
```

### Screen 2 — "Why Buy?" Detail Panel

```
┌─────────────────────────────────────────────────────────────┐
│  ← Back          BAJAJ FINANCE (BAJFINANCE)    [Add Watch]  │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Current Price: ₹6,842    DCF Base: ₹9,820   MoS: +31%    │
│                                                             │
│  LAYER SCORES                                              │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  Layer 1: Quality    ROCE 3yr: 18.4%   FCF: +ve  ✓ │   │
│  │  Layer 2: Safety     D/E: 0.4   Pledge: 0%   F:8  ✓ │   │
│  │  Layer 3: Valuation  Bear:₹7.2k  Base:₹9.8k  ▓▓▓▓ ✓│   │
│  │  Layer 4: Growth     EPS CAGR: 22%   OPM: +1.2%  ✓ │   │
│  │  Layer 5: Momentum   EMA✓  RSI:57  Vol:1.8x      ✓ │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  DCF SCENARIO CHART                                        │
│  ₹12k ┤                           ●  Bull ₹12,400         │
│  ₹10k ┤               ─────────── ●  Base ₹9,820          │
│   ₹8k ┤  ─ ─ ─ ─ ─ ─              ●  Bear ₹7,240          │
│   ₹6k ┤  ══ Current Price ₹6,842                          │
│        └────────────────────────────                       │
│                                                             │
│  EXIT PLAN                                                 │
│  Stop-loss: ₹5,815 (-15%)   Trailing: 20% off peak        │
│  Review trigger: ROCE < 12% for 2 quarters                 │
│                                                             │
│  [ Set Position Size ]   [ Add to Watchlist ]              │
└─────────────────────────────────────────────────────────────┘
```

### Screen 3 — DCF Calculator

```
┌─────────────────────────────────────────────────────────────┐
│  DCF SCENARIO CALCULATOR                                    │
├────────────────────────────┬────────────────────────────────┤
│  INPUTS                    │  RESULTS                       │
│                            │                                │
│  Current FCF (₹ Cr)        │  ┌──────┬──────┬──────┐      │
│  [  500              ]     │  │ Bear │ Base │ Bull │      │
│                            │  ├──────┼──────┼──────┤      │
│  FCF Growth Rate %         │  │₹7.2k │₹9.8k │₹12.4k│      │
│  [  14               ]     │  └──────┴──────┴──────┘      │
│                            │                                │
│  WACC %                    │  Margin of Safety              │
│  [  12               ]     │  [████████████░░░░░░░] +31%   │
│                            │                                │
│  Current Market Price      │  ✓ PASS Layer 3               │
│  [  6842              ]    │  Price < 80% of Base IV        │
│                            │                                │
│  [ Recalculate ]           │  EV/EBITDA: 11.2× ✓           │
└────────────────────────────┴────────────────────────────────┘
```

### Screen 4 — Portfolio Tracker

```
┌─────────────────────────────────────────────────────────────┐
│  MY PORTFOLIO                          Total: ₹2,42,800     │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Sector Distribution                 Position Limits       │
│  ┌────────────────────┐              Max per stock: 5%      │
│  │ NBFC     ▓▓▓▓ 24% │              Max per sector: 30%    │
│  │ Consumer ▓▓▓  18% │              ⚠ NBFC near limit      │
│  │ IT       ▓▓   12% │                                     │
│  │ Pharma   ▓    8%  │                                     │
│  └────────────────────┘                                     │
│                                                             │
│  POSITIONS                                                  │
│  ┌────────────────────────────────────────────────────────┐ │
│  │ Stock    Qty  Entry   CMP    P&L     Stop    Status    │ │
│  ├────────────────────────────────────────────────────────┤ │
│  │ BAJFIN    7  ₹6,420  ₹6,842  +6.5%  ₹5,815  Active   │ │
│  │ PIDLIT   12  ₹2,180  ₹2,310  +6.0%  ₹1,853  Active   │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                             │
│  ALERTS                                                     │
│  ⚠ BAJFIN: RSI has crossed 68 — monitor for exit          │
│  ℹ PIDLIT: Momentum score weakened (EMA crossover pending) │
└─────────────────────────────────────────────────────────────┘
```

### Screen 5 — Audit Log

```
┌─────────────────────────────────────────────────────────────┐
│  AUDIT LOG            [Filter: All ▼] [Export CSV]         │
├──────────────────────┬──────────┬────────────┬─────────────┤
│  Timestamp           │ Ticker   │ Decision   │ Reason      │
├──────────────────────┼──────────┼────────────┼─────────────┤
│ 2025-01-12 21:04:32  │ INFY     │ PASS       │ All 4 layers│
│ 2025-01-12 21:03:51  │ TITAN    │ FAIL L3    │ MoS: -8%    │
│ 2025-01-12 21:03:12  │ ZOMATO   │ SKIP       │ 3 NaN metrics│
│ 2025-01-12 21:02:44  │ ADANIPRT │ FAIL L2    │ D/E: 2.4    │
│ 2025-01-12 20:58:10  │ NESTLEIND│ OUTLIER    │ DCF > 300%  │
└──────────────────────┴──────────┴────────────┴─────────────┘
```

---

## 8. Development Roadmap

| Phase | Name | Effort | Status |
|-------|------|--------|--------|
| 1 | Engine A — Fundamental Screener | 2–3 weeks | To build |
| 2 | DCF Valuation Engine | 1 week | To build |
| 3 | Engine B — Momentum Scanner | 1–2 weeks | To build |
| 4 | Streamlit Dashboard | 2 weeks | To build |
| 5 | Backtesting & Validation | 3–4 weeks | To build |
| 6 | Paper Trading (8–12 weeks) | 8–12 weeks | Gate before real capital |

**Total timeline before deploying real money: ~5–6 months**

---

## 9. Phase-by-Phase Dev Instructions

### Phase 1 — Engine A: Fundamental Screener

**File structure:**

```
engine_a/
├── main.py              # Entry point, loops tickers
├── data_fetcher.py      # yfinance wrappers with retry
├── layer1_quality.py    # ROCE + FCF checks
├── layer2_safety.py     # D/E, pledging, F-Score
├── layer3_valuation.py  # DCF engine
├── layer4_growth.py     # EPS/OPM/Revenue checks
├── audit_logger.py      # Structured JSONL logging
├── config.yaml          # All thresholds
└── output/
    └── qualified_universe.csv
```

**main.py skeleton:**

```python
import pandas as pd
import yaml
from pathlib import Path
from datetime import datetime
from data_fetcher import fetch_with_retry
from layer1_quality import check_layer1
from layer2_safety import check_layer2
from layer3_valuation import check_layer3
from layer4_growth import check_layer4
from audit_logger import audit_log

def run_engine_a():
    config = yaml.safe_load(open("config.yaml"))
    tickers = pd.read_csv("data/nifty500.csv")['Symbol'].tolist()
    results = []

    for ticker in tickers:
        data = fetch_with_retry(ticker)
        if data is None:
            continue

        # Run layers in sequence; fail fast
        p1, m1 = check_layer1(data, config)
        if not p1:
            audit_log(ticker, "FAIL_L1", "Quality gate failed", m1)
            continue

        p2, m2 = check_layer2(data, config)
        if not p2:
            audit_log(ticker, "FAIL_L2", "Safety gate failed", m2)
            continue

        p3, m3 = check_layer3(data, config)
        if not p3:
            audit_log(ticker, "FAIL_L3", "Valuation gate failed", m3)
            continue

        p4, m4 = check_layer4(data, config)
        if not p4:
            audit_log(ticker, "FAIL_L4", "Growth gate failed", m4)
            continue

        audit_log(ticker, "PASS", "All 4 layers passed", {**m1, **m2, **m3, **m4})
        results.append({"ticker": ticker, **m1, **m2, **m3, **m4})

    df = pd.DataFrame(results)
    df['last_updated'] = datetime.now().isoformat()
    df.to_csv("output/qualified_universe.csv", index=False)
    print(f"Engine A complete: {len(df)} qualified stocks out of {len(tickers)}")

if __name__ == "__main__":
    run_engine_a()
```

**Scheduling (cron):**

```bash
# Run every Sunday at 9 PM IST (3:30 PM UTC)
30 15 * * 0 cd /path/to/project && python engine_a/main.py >> logs/engine_a.log 2>&1
```

---

### Phase 2 — DCF Valuation Engine

See full code in Section 4. Key testing requirement:

```python
# Test with known company data before deployment
def test_dcf_sanity():
    # Should produce reasonable results for a well-known company
    result = calculate_dcf(
        current_fcf=500,
        fcf_growth_rate=0.14,
        current_price=6842,
        config=load_config()
    )
    assert result.verdict in ["PASS", "FAIL", "OUTLIER"]
    assert 0 < result.base < 1_000_000  # Sanity: must be a real number
    assert result.bear < result.base < result.bull  # Monotonic
```

---

### Phase 3 — Engine B: Momentum Scanner

**File structure:**

```
engine_b/
├── main.py               # Entry point
├── freshness_check.py    # Circuit breaker
├── layer5_momentum.py    # EMA, RSI, Volume
├── regime_filter.py      # Nifty 200-EMA check
└── output/
    └── ranked_candidates.csv
```

**layer5_momentum.py:**

```python
import pandas as pd
import yfinance as yf
from ta.momentum import RSIIndicator
from ta.trend import EMAIndicator

def check_layer5(ticker: str, config: dict) -> tuple[bool, dict]:
    cfg = config['layer5_momentum']

    data = yf.download(ticker + ".NS", period="1y", interval="1d", progress=False)
    if data.empty or len(data) < 200:
        return False, {"reason": "insufficient_price_history"}

    close = data['Close']
    volume = data['Volume']

    ema20 = EMAIndicator(close, window=20).ema_indicator().iloc[-1]
    ema50 = EMAIndicator(close, window=50).ema_indicator().iloc[-1]
    ema200 = EMAIndicator(close, window=200).ema_indicator().iloc[-1]
    rsi = RSIIndicator(close, window=14).rsi().iloc[-1]
    vol_ratio = volume.iloc[-1] / volume.rolling(20).mean().iloc[-1]
    high_52w = close.rolling(252).max().iloc[-1]
    current = close.iloc[-1]

    # All conditions
    ema_cross = ema20 > ema50
    above_200 = current > ema200
    rsi_ok = cfg['rsi_min'] < rsi < cfg['rsi_max_entry']
    vol_ok = vol_ratio > cfg['volume_ratio_min']
    not_near_high = current < high_52w * (1 - cfg['high_52w_buffer_pct'] / 100)

    passes = ema_cross and above_200 and rsi_ok and vol_ok and not_near_high

    return passes, {
        "ema20": round(ema20, 2), "ema50": round(ema50, 2),
        "ema200": round(ema200, 2), "rsi": round(rsi, 1),
        "volume_ratio": round(vol_ratio, 2),
        "near_52w_high": not not_near_high,
        "ema_cross": ema_cross, "above_200ema": above_200
    }
```

---

### Phase 4 — Streamlit Dashboard

**File structure:**

```
dashboard/
├── app.py                  # Main Streamlit app
├── pages/
│   ├── 1_universe.py       # Qualified universe table
│   ├── 2_stock_detail.py   # Why Buy? panel
│   ├── 3_dcf_calculator.py # Interactive DCF tool
│   ├── 4_portfolio.py      # Position tracker
│   └── 5_audit_log.py      # Audit log viewer
├── components/
│   ├── layer_scorecard.py  # Reusable 5-layer badge component
│   ├── dcf_chart.py        # Bear/Base/Bull chart
│   └── regime_banner.py    # Market regime status
└── utils/
    └── data_loader.py      # CSV reader with caching
```

**app.py (entry point):**

```python
import streamlit as st

st.set_page_config(
    page_title="TradeFilter",
    page_icon="◈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Regime banner at top of every page
from components.regime_banner import show_regime_banner
show_regime_banner()
```

**Key Streamlit patterns:**

```python
# Cache data loading — refresh every hour during market hours
@st.cache_data(ttl=3600)
def load_universe():
    return pd.read_csv("engine_a/output/qualified_universe.csv")

# Show 5-layer scorecard as color-coded badges
def layer_badge(passed: bool, label: str):
    color = "green" if passed else "red"
    icon = "✓" if passed else "✗"
    st.markdown(
        f'<span style="background:{color};color:white;'
        f'padding:2px 8px;border-radius:4px;font-size:12px">'
        f'{icon} {label}</span>',
        unsafe_allow_html=True
    )
```

---

### Phase 5 — Backtesting & Go-Live Gate

**Do not skip this phase.** Before deploying any real capital:

1. **Backtest Engine A** on Nifty 500 historical data (minimum 5 years: 2019–2024).
   - Tool: `backtesting.py` or `vectorbt`
   - Target: Sharpe Ratio > 1.0, Max Drawdown < 25%

2. **Validate F-Score** — confirm your F-Score implementation matches known values for well-documented companies.

3. **Paper trade for 8–12 weeks:**
   - Run both engines in production mode
   - Log every signal as if you placed a real trade
   - Compare simulated P&L vs Nifty benchmark at end of period

4. **Go-live capital limit:**
   - Start with maximum ₹50,000 regardless of portfolio size
   - After 6 months of live results, evaluate increasing allocation
   - Never allocate more than 20% of total savings to this strategy

---

## 10. Tech Stack & Dependencies

### Python Environment

```
python >= 3.11
yfinance >= 0.2.40
pandas >= 2.0
numpy >= 1.26
ta >= 0.11           # Technical analysis indicators
pyyaml >= 6.0
streamlit >= 1.35
plotly >= 5.20
backtesting >= 0.3.3  # For Phase 5
```

### requirements.txt

```
yfinance==0.2.40
pandas==2.0.3
numpy==1.26.4
ta==0.11.0
pyyaml==6.0.2
streamlit==1.35.0
plotly==5.22.0
requests==2.31.0
python-dateutil==2.9.0
```

### Data Sources

| Data | Primary Source | Backup / Cross-check |
|------|---------------|---------------------|
| Fundamental data | yfinance | Screener.in (manual validation) |
| Price / volume | yfinance | NSE official data |
| Nifty 500 list | NSE website (monthly update) | Screener.in |
| Corporate actions | yfinance adjusted prices | NSE announcements |
| Promoter pledging | BSE filings via yfinance | Trendlyne |

### Infrastructure

- **Engine A:** Local Python script, scheduled via cron (or GitHub Actions for cloud)
- **Engine B:** Local Python script, run manually before market analysis
- **Dashboard:** Streamlit Cloud (free tier) or local `streamlit run app.py`
- **Logs:** Local JSONL files in `logs/` directory; commit weekly snapshots to git

---

## 11. Testing & Validation Checklist

### Before First Run

- [ ] All thresholds in `config.yaml` reviewed and understood
- [ ] DCF function produces monotonic results (bear < base < bull)
- [ ] Null handler tested with artificially missing data
- [ ] Circuit breaker tested with an old CSV timestamp
- [ ] Audit logger writes valid JSONL

### Weekly (Engine A)

- [ ] Output CSV contains `last_updated` timestamp
- [ ] At least 30+ stocks pass (if < 10, check API or threshold issue)
- [ ] No DCF outliers > 5% of total processed
- [ ] Sanity-check 3 random "PASS" stocks manually on Screener.in

### Daily (Engine B)

- [ ] Market regime check runs before any signals
- [ ] Volume data is from today's trading session
- [ ] No signals generated when Nifty < 200 EMA

### Monthly

- [ ] Re-download Nifty 500 ticker list (composition changes quarterly)
- [ ] Review audit log for pattern anomalies
- [ ] Compare 3 actual pass → signal stocks vs their subsequent performance
- [ ] Revalidate yfinance data against Screener.in for 5 random tickers

---

## 12. Appendix: Key Formulas

### ROCE

```
ROCE = EBIT / Capital Employed
Capital Employed = Total Assets − Current Liabilities
Use 3-year average: (ROCE_yr1 + ROCE_yr2 + ROCE_yr3) / 3
```

### Free Cash Flow

```
FCF = Operating Cash Flow − Capital Expenditure
3yr cumulative = FCF_yr1 + FCF_yr2 + FCF_yr3
```

### DCF Base Case

```
Intrinsic Value = Σ(FCF_t / (1+WACC)^t) + Terminal Value / (1+WACC)^5

Where:
  FCF_t = FCF_0 × (1 + g)^t
  Terminal Value = FCF_5 × (1 + TGR) / (WACC - TGR)
  TGR = Terminal Growth Rate (3%)
  WACC = Risk-Free Rate + Equity Risk Premium (~11.5%)
```

### Margin of Safety

```
MoS% = (Base IV − Current Price) / Base IV × 100
Buy signal: MoS% ≥ 20%
```

### Piotroski F-Score

```
Score = Σ of 9 binary signals (0 or 1 each)
Signals: ROA positive, OCF positive, ROA improving,
         Accruals (OCF > ROA), Debt ratio falling,
         Current ratio improving, No dilution,
         Gross margin improving, Asset turnover improving
```

### EPS CAGR

```
EPS CAGR = (EPS_latest / EPS_3yr_ago)^(1/3) − 1
Expressed as percentage
```

### RSI (14-day)

```
RS = Average Gain (14d) / Average Loss (14d)
RSI = 100 − (100 / (1 + RS))
```

---

*Document version: 2.0 | Last updated: January 2025*
*For personal use only. This is not financial advice.*