"""Capital and threshold constants for Nifty conviction scanner."""

TOTAL_CAPITAL = 1_000_000
MAX_DEPLOYED = 250_000
CORE_BUFFER = 600_000
RESERVE = 150_000
BUFFER_FLOOR = 450_000  # 75% of core buffer — stop new trades below this

GAP_REVIEW_THRESHOLD = 150  # points — forced review above this
GAP_KILL_THRESHOLD = 200  # points — kill-switch territory
MIN_PREMIUM_PER_LEG = 40  # ₹ per share — premium quality floor
DAILY_LOSS_KILL_PCT = 4.0  # % of total capital

# Short-vol friendly regime: spot within this range of 200 SMA
SMA200_NEUTRAL_BAND_PCT = 3.0

# IV percentile bands (India VIX vs 1-year range)
IV_PCT_MIN = 15
IV_PCT_MAX = 75

# OTM ladder distances for proposed strikes (points from spot)
PE_LADDER_OFFSETS = [200, 250, 300, 350, 400]
CE_LADDER_OFFSETS = [200, 250, 300]

FIRST_ENTRY_DEPLOY_PCT = 0.30  # 30% of max deployed on first entry

RESULTS_CSV = "data/conviction_results.csv"
BLACKOUT_CSV = "data/blackout_calendar.csv"
OUTPUT_JSON = "output/nifty_setup.json"
