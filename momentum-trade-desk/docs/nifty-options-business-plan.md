# Nifty Options — Conviction-Based Trading Plan
**Capital: ₹10,00,000 (fixed) | Style: High-conviction only, no fixed income target**

> Idea-level framework, not financial advice. Treat as a personal business plan you can pressure-test, not a promise of returns.

---

## 0) Core shift from the original plan

The original framing was **₹10k/month fixed target → back-solve capital needed**. That's the wrong direction for a business — it pressures you to trade when there's no edge, just to "hit the number."

**New framing:** ₹10L is fixed. You don't scale capital up or down. What varies is **how much of it you deploy, and when** — driven by conviction, not calendar.

| Old model | New model |
|---|---|
| Fixed ₹10k/month target | No fixed monthly target — track P&L, don't chase it |
| Weekly ladder every week | Trade only when setup criteria are met |
| Capital sized to hit income goal | Capital fixed at ₹10L; position sizing flexes with conviction |
| "Time to sell" (Friday routine) | "Is this a setup?" (conditional routine) |

---

## 1) Capital structure (fixed at ₹10L)

| Bucket | Amount | Purpose |
|---|---|---|
| **Total capital** | ₹10,00,000 | Hard ceiling — never add more |
| **Max deployed (any time)** | ₹2,50,000 (25%) | Even on your highest-conviction week |
| **Core buffer** | ₹6,00,000 (60%) | Absorbs adjustments, gap opens |
| **Reserve / do-not-touch** | ₹1,50,000 (15%) | Only unlocked in a pre-defined crisis protocol, never for "one more adjustment" |

Rules:
- Deployed capital never exceeds ₹2.5L, regardless of how good a setup looks. Conviction changes **which** trades you take, not the ceiling.
- If buffer (the ₹6L) drops below ₹4.5L (75% of itself), you stop opening new positions until it recovers.
- The ₹1.5L reserve is not "extra ammo" — it's what keeps you solvent through a genuine tail event (2020/2024-style). Touching it should feel like a five-alarm event, not routine.

---

## 2) What "high conviction" means (define this before you trade)

A trade is only high-conviction if it passes **all** of these — not most:

1. **Regime check:** Nifty trend + IV percentile support the trade (not fighting a strong trend with a short-vol bet)
2. **Event check:** No major event (RBI, Budget, Fed, expiry-week gamma risk) inside your holding window, unless the trade is specifically structured for that event
3. **Premium quality:** Premium you're collecting is meaningfully above your minimum threshold (define a number, e.g. ₹40+ per leg) — not chasing token premium just to "do something"
4. **Risk-reward is explicit:** You can state, before entry, your max loss, your adjustment trigger, and your hard exit — in writing, not in your head
5. **You'd take this trade with someone watching:** A gut check against boredom-trading or FOMO-trading

If a week doesn't produce a setup meeting all five, **you don't trade that week.** Zero trades is a valid outcome, not a failure.

---

## 3) Engines, reframed for conviction (not calendar)

### Engine A — Entry (event-driven, not day-of-week-driven)
- No default "sell every Friday." Entry happens only when the conviction checklist (Section 2) is fully met.
- When it is met: ladder entry as before (3–5 PE strikes, 2–3 CE strikes), but capped at 25–35% of the ₹2.5L deployed ceiling on first entry — leave room to scale into the *same* high-conviction trade if it develops well, rather than spreading thin across mediocre setups.

### Engine B — Adjustment (unchanged mechanics, stricter trigger)
Same tools as before (trend hedge, delta-to-theta conversion, margin recycling), but adjustments only fire if the *original* trade still meets your conviction criteria. If the thesis is broken (not just the price moved), the correct move is often exit, not adjust.

### Engine C — Exit / risk
- Close 1 day before expiry, no new naked sells after Wednesday of expiry week — unchanged.
- Add: **post-trade review is mandatory**, win or lose. Every closed trade gets a one-line note: was this actually high-conviction, or did discipline slip? This is how "business" stays honest over "hobby."

---

## 4) Business-style tracking (replaces the ₹10k/month scoreboard)

Track these instead of a fixed income number:

- **Trade count per month** — low is fine, expected even
- **Win rate on conviction-qualified trades only** — this tells you if your filter works
- **Average R multiple** (return relative to max planned loss) per trade
- **Max drawdown vs the ₹6L buffer** — did it ever breach 75%?
- **Discipline log** — trades taken that *didn't* meet all 5 criteria (target: zero)

A good month might be one trade and ₹0 income. A bad month is trading without a qualifying setup, not the absence of income.

---

## 5) App / tooling implications (built for conviction, not calendar)

Adjust the original app modules:

- **Module 1 (Regime filter)** stays — this now gates whether a setup *can* exist, not whether you trade on schedule.
- **Module 3 (Rule engine)** changes from a day-of-week state machine to a **conditional state machine**: `WAITING_FOR_SETUP → QUALIFIED → SELLING → ADJUSTING → DE_RISK → FLAT`. The system should be comfortable sitting in `WAITING_FOR_SETUP` for weeks.
- **New Module 6 — Conviction scorer:** a simple checklist UI where you score the 5 criteria before any entry is allowed. If any box is unchecked, the app blocks the trade (or requires explicit override + a logged reason).
- **Module 5 (Backtest)** should specifically report: how many *weeks had no qualifying setup*, and what P&L looked like when you only took the high-conviction subset vs. trading every week. This tells you whether selectivity is actually adding value or just reducing sample size.

---

## 6) Phased rollout (capital never changes, only trade frequency)

**Phase 1 — Paper (8–12 weeks)**
- Full ₹10L structure simulated, but paper only.
- Goal: see how many weeks actually produce a qualifying setup. If it's "every week," your criteria are too loose.

**Phase 2 — Live, small (3 months)**
- Real money, but cap deployed at ₹1L (not the full ₹2.5L) even on qualifying setups, until you've proven the process live.
- 1 lot per strike, manual approval on every adjustment.

**Phase 3 — Scale to full ₹2.5L deployed ceiling only if:**
- Paper + live combined show buffer was never breached
- Discipline log stayed at zero non-qualifying trades
- You're comfortable with months that produce no trades at all

---

## 8) Black swan & gap risk — dedicated defenses

The original plan treated the buffer as the main gap defense. That's necessary but not sufficient — a buffer absorbs the *margin* hit, but it doesn't stop a bad gap from being a bad gap. You need defenses that act *before* and *during* the event, not just capital that survives after it.

### 8.1 Pre-market / overnight gap checks (every single day you hold a position)
- Check GIFT Nifty (formerly SGX Nifty) pre-market level every morning before 9:00 AM — this is your early warning for a gap.
- If GIFT Nifty implies a gap beyond a threshold you define (e.g. >150–200 points from previous close), treat it as a **forced review**, not a normal trading day: reassess every open position before market opens, don't wait for 9:15 to react.
- Never assume "it'll come back to range" as a plan. Gaps that open beyond your threshold get de-risked first, analyzed second.

### 8.2 Standing tail hedge ("black swan insurance")
- Carry a small, cheap, far-OTM protective position at all times when you have naked/short exposure — e.g. a far OTM put (400–600+ points away) sized to blunt a 1000+ point crash day, even though it will usually expire worthless.
- Cost this as a fixed "insurance premium" line item in your monthly tracking (Section 4), not as a failed trade. Its job is to make the tail survivable, not to be profitable.
- This is the single highest-leverage change vs. the original plan: buffer capital protects solvency; a tail hedge protects the *portfolio* directly on the day it matters.

### 8.3 Event calendar — hard blackout list
Maintain an explicit list of dates where new naked positions are blocked outright, and existing positions get reduced ahead of time (not reacted to after):
- RBI policy days, Union Budget, Fed FOMC days
- Major elections / election result days (state or national)
- Known geopolitical flashpoints (e.g. scheduled summits, ceasefire deadlines) when they're publicly known in advance
- Expiry-week Wednesday onward (already in your plan — keep it)
- Long weekends / market holidays adjacent to your positions — 3-day gap risk is materially higher than 1-day

Rule: reduce size **the day before**, not the morning of. Morning-of reactions are too late for a gap.

### 8.4 Portfolio-level circuit breakers (in addition to the buffer)
- **Daily loss kill-switch:** if MTM loss hits a pre-defined % of total capital (you set this, e.g. 3–5%) in a single session, all new selling stops for the rest of that day — no exceptions, no "it'll recover."
- **Gap-day kill-switch:** if the market gaps beyond your threshold (8.1) *and* it's against your position, the default action is de-risk first, adjust second. Don't let adjustment logic (Engine B) run before the de-risk check.
- **Correlation check:** confirm your PE and CE ladder isn't accidentally net-directional (e.g. too many uncovered PEs) right before a binary event — a portfolio that looks "hedged" in calm markets can be quietly directional.
- **Liquidity check:** avoid strikes with wide bid-ask spreads or thin open interest — in a fast gap, illiquid strikes are the ones you can't exit at a sane price.

### 8.5 Historical stress scenarios to explicitly test (Module 5 backtest)
Don't just backtest "normal" years. Explicitly run the strategy through:
- March 2020 (COVID crash — multi-day, high-vol crash)
- A budget-day or election-result single-day gap (large single-day move)
- A low-liquidity holiday-adjacent gap
- A slow grind-down (theta didn't help — trend just ran against you for weeks)

Report the same metrics as before (Section 4) *for these scenarios specifically*, not blended into an average. If the strategy survives the average year but blows through the buffer in any one of these, that's the constraint that matters — not the average.

---

## 9) Basic defensive checklist (use before every trade and every trading day)

**Before opening any new position (in addition to the 5 conviction criteria in Section 2):**
- [ ] GIFT Nifty pre-market gap checked and within threshold
- [ ] No blackout-list event in the holding window (8.3)
- [ ] Standing tail hedge is in place and sized correctly for current deployed capital
- [ ] Strike liquidity checked (bid-ask spread acceptable)
- [ ] Deployed capital after this trade stays within the ₹2.5L ceiling

**Every trading day you hold a position (regardless of new trades):**
- [ ] Pre-market gap check done
- [ ] Buffer still above the 75%-of-₹6L threshold
- [ ] Daily loss kill-switch level confirmed (know the number before the day starts, not after a bad move)
- [ ] Tail hedge still in place (didn't get closed as "dead weight" during a margin recycle)

**Weekly (Friday close or session review):**
- [ ] Discipline log updated — any trade taken outside the conviction checklist?
- [ ] Buffer, deployed capital, and reserve reconciled against the ₹10L total
- [ ] Upcoming week checked against the blackout calendar

---

## 10) Automation idea — Git + cron pipeline for backtest / live paper test

A simple, auditable architecture: cron runs a script on schedule, the script pulls data and evaluates your rules, and results get appended as rows to a CSV in a `data/` folder — with git used as your immutable audit trail (every run is a commit, so you have a tamper-evident history of every signal and result, not just a mutable spreadsheet).

### Repo structure
```
nifty-strategy/
├── strategy/
│   ├── conviction_checklist.py   # Section 2 rules as code
│   ├── regime_filter.py          # Module 1: trend/IV/event checks
│   ├── gap_check.py              # Section 8.1: GIFT Nifty gap check
│   ├── position_sizing.py        # Section 1 capital rules
│   └── kill_switches.py          # Section 8.4 circuit breakers
├── data/
│   ├── results.csv               # append-only: one row per run
│   └── blackout_calendar.csv     # Section 8.3 event dates
├── scripts/
│   ├── run_daily_check.py        # main entrypoint, called by cron
│   └── run_backtest.py           # historical run, separate from live
├── logs/
│   └── run_YYYY-MM-DD.log
└── README.md
```

### `results.csv` columns (one row appended per run)
```
run_date, run_type(backtest|paper|live), setup_qualified(bool),
conviction_score(0-5), regime_status, gap_points, blackout_flag,
deployed_capital, buffer_capital, action_taken, pnl_day, pnl_cumulative,
max_drawdown_to_date, kill_switch_triggered, notes
```

### Cron job (runs the pre-market check + logs the day's decision)
```bash
# crontab -e — runs 8:45 AM IST on weekdays, before market open
45 8 * * 1-5 cd /path/to/nifty-strategy && /usr/bin/python3 scripts/run_daily_check.py >> logs/run_$(date +\%F).log 2>&1
```

### `run_daily_check.py` — high-level flow (pseudocode, not a full trading system)
```python
import csv, datetime
from strategy import regime_filter, gap_check, conviction_checklist, kill_switches

def run():
    today = datetime.date.today()

    # 1. Pull data (GIFT Nifty, spot, IV, VIX — via your data source)
    gap = gap_check.get_overnight_gap()
    regime = regime_filter.get_regime_status()
    blackout = regime_filter.is_blackout_day(today)

    # 2. Evaluate conviction checklist (Section 2) — returns score 0-5
    score = conviction_checklist.evaluate(gap, regime, blackout)

    # 3. Kill-switch checks run BEFORE any "should I trade" logic
    kill_triggered = kill_switches.check(gap, regime)

    # 4. Decide action — this is a PROPOSAL, not auto-execution
    if kill_triggered or blackout or score < 5:
        action = "NO_TRADE"
    else:
        action = "QUALIFIED_SETUP"  # flagged for manual review/approval

    # 5. Append one row to results.csv — never overwrite, always append
    row = [today, "live_paper", score == 5, score, regime, gap,
           blackout, None, None, action, None, None, None,
           kill_triggered, ""]
    with open("data/results.csv", "a", newline="") as f:
        csv.writer(f).writerow(row)

if __name__ == "__main__":
    run()
```

### Why git matters here (not just cron + CSV)
- After the script runs, a second cron step (or the script itself) does `git add data/results.csv && git commit -m "run: $(date +%F)"`. This gives you a **timestamped, tamper-evident log** of every decision the system made — including every day it correctly chose *not* to trade. That log is exactly what Section 4's "discipline log" and Section 8.5's stress-test reporting need, and it's much harder to quietly edit after the fact than a spreadsheet.
- For `run_backtest.py`, same pattern but looping over historical dates (including the stress scenarios in 8.5) instead of "today" — writes to a separate `backtest_results.csv` so live and historical data never mix.
- Start this whole pipeline in **paper mode only** (Phase 1 in Section 6). The script should never place real orders on its own — it proposes, you approve, consistent with the "approval mode → semi-auto → full auto" progression from the original plan.

---

## 11) Key mindset differences from the original plan

- **No monthly quota.** The moment ₹10,000/month becomes the goal, every mediocre setup starts looking "good enough." Removing the number removes that pressure.
- **Capital is fixed, not a lever.** You don't ask "how much capital do I need for X income" — you ask "what's the best use of this ₹10L this week, if any."
- **Zero trades is a business decision, not idle time.** A fund manager holding cash in a bad regime is doing their job.
- **The buffer's job is survival, not backup ammo.** Treat the ₹1.5L reserve as effectively inaccessible in normal operation.
