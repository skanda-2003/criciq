# CricIQ: IPL Tactical Analytics Dashboard

## Project Overview

CricIQ is a full-stack cricket analytics project built around ball-by-ball IPL data. The goal is to answer questions that IPL coaching staff and analysts actually care about — not just batting averages, but phase-based performance, bowler matchups, venue effects, win probability, and a composite player impact metric.

## Tech Stack

- **Language**: Python 3.11
- **Data**: Pandas, NumPy
- **ML**: Scikit-learn, Scipy
- **Visualization**: Matplotlib, Seaborn, Plotly
- **Dashboard**: Streamlit
- **Environment**: Jupyter Notebooks for analysis → `.py` files for the Streamlit app

## Data Sources

- **Primary**: Cricsheet IPL data (cricsheet.org) — ball-by-ball JSON/CSV for every IPL match since 2008. 1000+ matches, every delivery recorded.
- **Secondary**: Kaggle IPL Player Performance Dataset — career aggregates and auction prices for player valuation angle.

## Project Structure (Target)

```
criciq/
├── data/
│   ├── raw/            # Cricsheet JSON files and Kaggle CSVs
│   └── processed/      # Cleaned flat DataFrames (ball-by-ball, match-level)
├── notebooks/          # Jupyter notebooks for EDA and each analysis angle
├── src/                # Python modules (data parsing, feature engineering, models)
├── app/                # Streamlit dashboard pages
├── models/             # Saved model artifacts
└── CLAUDE.md
```

## Core DataFrames

Two primary DataFrames drive all analysis:

1. **Ball-by-ball DataFrame** — one row per delivery. Columns: `match_id`, `innings`, `over`, `ball`, `batsman`, `bowler`, `runs_scored`, `wicket`, `extras`, `venue`, `season`, `match_result`
2. **Match-level summary DataFrame** — one row per match with aggregated totals and result

## The 5 Analysis Angles

### Angle 1 — Phase-wise Batting Analysis
- Phases: Powerplay (overs 1–6), Middle (7–15), Death (16–20)
- Metrics per batsman per phase: strike rate, boundary %, dot ball %
- Question: Who accelerates in the death? Who struggles in the powerplay?

### Angle 2 — Bowler Matchup Analysis
- Filter: bowler-batsman combinations with >20 balls faced
- Metrics: runs per ball, dismissal probability, boundary rate
- Output: matchup heatmap matrix

### Angle 3 — Venue and Pitch Impact
- Compare scoring at different venues (e.g. Wankhede vs Chepauk)
- Use t-tests (Scipy) to test statistical significance of venue differences
- Report p-values — this makes it research-grade, not just descriptive

### Angle 4 — Win Probability Model (ML centrepiece)
- Features: current run rate, required run rate, wickets in hand, overs remaining, venue (encoded), batting team (encoded)
- Models: Logistic Regression (baseline) → Random Forest
- Evaluation: accuracy, ROC-AUC, calibration curve
- Output: ball-by-ball win probability shifts for a sample match

### Angle 5 — Player Impact Score (original metric)
- Composite score weighing batting contribution, bowling economy, and fielding (catches, run outs)
- Produces a per-match impact score and season leaderboard
- Goal: identify players who outperform their reputation by this metric

## Streamlit Dashboard (4 Pages)

1. **Overview** — season-wise trends, top performers
2. **Player Deep-Dive** — select any player → phase stats, matchup heatmap, impact score trend
3. **Match Simulator** — input match state → win probability gauge
4. **Head-to-Head** — compare any two franchises across seasons

## Build Timeline

| Week | Focus |
|------|-------|
| 1 | Data ingestion: parse Cricsheet JSONs, flatten to DataFrames, clean names |
| 2 | EDA + all 5 analysis angles in Jupyter, Plotly visualizations |
| 3 | Win probability model, player impact score, model evaluation |
| 4 | Streamlit dashboard, GitHub README, demo recording |

## Key Implementation Notes

- Cricsheet JSON is **nested** — flattening takes care; budget time for this in Week 1
- Player names vary across seasons — build a **name mapping dictionary** to standardise
- Calibration curve is essential for win probability model — it validates that predicted probabilities are reliable
- The venue t-test p-values should be reported explicitly in the dashboard and README

## Commands

```bash
# Install dependencies
pip install pandas numpy scikit-learn scipy matplotlib seaborn plotly streamlit

# Run Streamlit app
streamlit run app/main.py

# Run notebooks
jupyter notebook notebooks/
```
