# CricIQ - IPL Tactical Analytics Dashboard

A full-stack cricket analytics project built on ball-by-ball IPL data. The goal is to answer questions that coaching staff and analysts actually care about - not just career averages, but phase-specific performance, bowler matchups, venue effects, win probability, and a composite player impact metric built from first principles.

Built with Python, Pandas, Scikit-learn, and Plotly Dash. Analysis spans 1,175 IPL matches and 279,586 deliveries from 2008 to 2026.

---

## Dashboard

Eight pages, each answering a distinct analytical question.

| Page | Question it answers |
|------|---------------------|
| **Overview** | How does scoring and performance break down across seasons and phases? |
| **Player Deep-Dive** | What does a player's full profile look like - batting, bowling, impact, matchups? |
| **Batting Analytics** | Who are the best batters in each phase of the innings? |
| **Bowler Analytics** | Who are the most economical death bowlers and powerplay wicket-takers? |
| **Allrounders** | Who genuinely contributes in both departments, and who is one-dimensional? |
| **Match Simulator** | Given a chase state, what is the win probability and how do scenarios change it? |
| **Head-to-Head** | How do two franchises compare across all their meetings? |
| **Team Strategy** | What are a franchise's tactical tendencies - by phase, by venue, by season? |

All pages respond to a season filter (default: 2021-26). This keeps the analysis relevant to modern T20 cricket, which is structurally different from the 2008-2015 era in batting aggression and death-over tactics.

---

## Key Findings

These came out of the analysis and are surfaced in the dashboard - I wrote the hypotheses before running any numbers.

**Venue**
- Wankhede is not a batting paradise. In 2021-26 it is statistically below the league average (p = 0.014, Cohen's d = -0.02). Delhi, Bengaluru, and Kolkata are the actual high-scoring grounds.
- Chennai (Chepauk) is the hardest venue to bat at in this era - lowest run rate with the largest negative effect size (d = -0.10, p < 0.001). Bowling-first at Chepauk is backed by data.

**Batting**
- Death specialists are a distinct archetype from openers who survive to the death. Filtering by average batting position > 5 correctly separates genuine finishers (Rinku Singh, Tim David, Shashank Singh) from well-settled openers.
- Complete batsmen are rare. Only a small number of players qualify with 50+ balls faced in both the powerplay and death phases.

**Win Probability Model**
- The engineered feature `run_rate_pressure` (= required run rate / current run rate) ranked as a top-3 feature importance in the Random Forest model, validating the domain-motivated approach over using raw rates independently.

**Allrounders**
- Of the 57 players who qualify with both batting (50+ balls faced) and bowling (50+ balls bowled) thresholds, only a subset have positive z-scores in both dimensions - meaning genuine elite allrounders are rarer than commentators suggest.

---

## Analysis Angles

The analysis is structured around five distinct angles, each in its own Jupyter notebook.

**1. Phase-wise Batting** (`notebooks/02_phase_batting.ipynb`)
Metrics per batsman per phase (powerplay / middle / death): strike rate, boundary %, dot ball %. Minimum 50 balls faced in each specific phase to qualify - thresholds are independent. Death specialist classification requires avg batting position > 5 to distinguish genuine finishers from openers.

**2. Bowler Matchup Analysis** (`notebooks/03_bowler_matchups.ipynb`)
798 bowler-batsman matchups at 20+ balls faced. Heatmaps for strike rate and dismissal probability. K-means clustering (k=4) on batsman vulnerability profiles across bowler types - produces archetypes like spin-vulnerable and pace-vulnerable. 36 batsmen eligible for clustering.

**3. Venue and Pitch Impact** (`notebooks/04_venue_impact.ipynb`)
Independent-sample t-tests comparing each venue's run rate against all others. Reports both p-value and Cohen's d - statistical significance alone does not tell you whether the difference is practically meaningful. 10 qualified venues (3+ seasons of data, not COVID-era UAE or 2022-only overflow grounds).

**4. Win Probability Model** (`notebooks/05_win_probability.ipynb`)
Logistic Regression baseline trained on 2019-2026 chase data. Features include current run rate, required run rate, run_rate_pressure (engineered), wickets in hand, overs remaining, venue, and batting team. Evaluated with accuracy, ROC-AUC, and a calibration curve - the calibration curve validates that predicted probabilities are actually reliable, not just that the classifier is accurate.

**5. Player Impact Score** (`notebooks/06_player_impact.ipynb`)
Composite metric: batting contribution vs phase average (50%), bowling economy vs venue average (35%), fielding from wicket records (15%). Weights are per-role - a pure batsman is not penalised for not bowling. Produces per-match scores and season leaderboards from 2021-26.

---

## Tech Stack

- **Language**: Python 3.11
- **Data processing**: Pandas, NumPy
- **ML / stats**: Scikit-learn (Logistic Regression, Random Forest, K-means), Scipy (t-tests, Cohen's d)
- **Visualization**: Plotly (all charts in the dashboard)
- **Dashboard**: Dash with Dash Bootstrap Components for layout
- **Notebooks**: Jupyter for EDA and analysis

---

## Data

**Primary source**: [Cricsheet](https://cricsheet.org) - ball-by-ball IPL data in JSON format, every match since 2008. Flattened into two canonical DataFrames at the start of the pipeline:

- `deliveries.csv` - 279,586 rows, one per delivery. Columns include phase, batting position, cumulative run rate, required run rate, run_rate_pressure, super_over flag, and all wicket metadata.
- `matches.csv` - 1,175 rows, one per match. Columns include toss decision, result margin, and player of the match.

**Secondary source**: Kaggle IPL Player Performance Dataset - career aggregates and auction prices.

Player name normalisation is handled by `src/name_map.py` since Cricsheet uses different spellings across seasons.

---

## Running the App

```bash
# Clone the repo
git clone https://github.com/skanda-2003/criciq.git
cd criciq

# Install dependencies
pip install -r requirements.txt

# Run the Dash app
python app.py
```

The app starts on `http://localhost:8050`. The win probability model retrains at startup (~2 seconds) - this is intentional since the saved `.pkl` files have a scikit-learn version mismatch.

To regenerate the processed CSVs from raw Cricsheet data:
```bash
python main.py
```

To run the analysis notebooks:
```bash
jupyter notebook notebooks/
```

---

## Project Structure

```
criciq/
├── app.py              # Dash entry point
├── pages/              # One file per page (8 pages total)
├── components/         # Reusable UI - metric_card, navbar, charts, theme
├── assets/style.css    # All styling (no inline styles except dynamic progress bars)
├── data/
│   ├── loader.py       # Shared DataFrame loader
│   ├── raw/            # Cricsheet JSONs and Kaggle CSVs
│   └── processed/      # deliveries.csv, matches.csv, and pre-computed analysis CSVs
├── notebooks/          # 6 notebooks: parser validation, 5 analysis angles
├── src/                # parser.py, name_map.py, wp_model.py
└── models/             # Saved encoder artifacts
```

---

## Known Limitations

These are worth knowing if you're extending the project or evaluating the analysis.

- **Fielding is incomplete**: Cricsheet only records catches and run-outs from wicket metadata. Direct throws, misfields, and fielding stops are not captured. The fielding component of the impact score is an undercount.
- **Win probability is 2nd innings only**: The current model only applies to chases. A 1st innings win probability model would need a different feature set and architecture.
- **Venue conditions change**: Pitch preparation at the same ground can shift across seasons. Restricting to 2021-26 reduces (but does not eliminate) this noise.
- **Name normalisation is incomplete**: `src/name_map.py` covers 202 known players but may miss edge cases for players with inconsistent Cricsheet spellings across seasons.
- **Auction price comparison is indicative**: Auction prices reflect expected future value, not just past performance. The "outperforming reputation" angle is interesting but not rigorous.
