"""
Main pipeline for CricIQ.

Run this file once to generate the processed CSVs:
    python main.py

It does four things in order:
  1. Parse all raw JSON files → deliveries_df and matches_df
  2. Standardise player names across seasons using the name map
  3. Add run-rate columns needed by the win probability model
  4. Save the final DataFrames to data/processed/
"""

from pathlib import Path

import numpy as np

from src.parser import parse_all
from src.name_map import build_name_map, apply_to_deliveries


PROCESSED_DIR = Path("data/processed")

# Total overs in an IPL innings (used to compute overs remaining)
TOTAL_OVERS = 20


def add_run_rate_columns(df):
    """Add current_run_rate, required_run_rate, and run_rate_pressure columns.

    These three columns are needed by the win probability model (Angle 4).
    They are computed from columns that already exist in the DataFrame after
    parsing: over, ball_in_over, cumulative_runs, target_runs, innings.

    Args:
        df: The deliveries DataFrame (modified in place).
    """

    # --- overs_completed ---
    # How many full overs have been bowled at the END of this delivery.
    # 'over' is 1-indexed, 'ball_in_over' counts only legal deliveries (1–6).
    # Formula: (over - 1) captures completed overs before the current over.
    # Adding ball_in_over / 6 gives fractional credit for the current over.
    # Example: over=3, ball_in_over=3 → 2 + 0.5 = 2.5 overs completed.
    # Wide/no-ball deliveries have ball_in_over=0, so they contribute 0 to
    # the fraction — they don't advance the over count, which is correct.
    overs_completed = (df["over"] - 1) + (df["ball_in_over"] / 6)

    # --- current_run_rate (CRR) ---
    # Runs scored so far divided by overs completed.
    # Set to NaN when overs_completed == 0 (the very first delivery of an
    # innings, before any full over is recorded) to avoid dividing by zero.
    crr = df["cumulative_runs"] / overs_completed
    crr[overs_completed == 0] = np.nan
    df["current_run_rate"] = crr

    # --- required_run_rate (RRR) — 2nd innings only ---
    # Runs still needed divided by overs still remaining in the innings.
    # Only meaningful when chasing, so we fill with NaN for innings 1.
    # overs_remaining = 20 - overs_completed (how many overs are left).
    overs_remaining = TOTAL_OVERS - overs_completed

    # Runs needed = target_runs - runs already scored.
    # target_runs is NaN for 1st innings rows, so the result is NaN there too.
    runs_needed = df["target_runs"] - df["cumulative_runs"]

    rrr = runs_needed / overs_remaining
    # If no overs remain (end of innings), set to NaN — division by zero.
    rrr[overs_remaining == 0] = np.nan
    rrr[runs_needed <= 0] = np.nan
    rrr = rrr.clip(upper = 36)
    df["required_run_rate"] = rrr

    # --- run_rate_pressure ---
    # Domain-motivated ratio: how fast does the team NEED to score vs how fast
    # are they CURRENTLY scoring?  Value > 1 means they're behind the chase.
    # Value of 2.0 means they need to score twice as fast as they currently are.
    # NaN wherever either CRR or RRR is NaN (i.e. 1st innings and over 0).
    df["run_rate_pressure"] = df["required_run_rate"] / df["current_run_rate"]
    df.loc[df["current_run_rate"].isnull() | (df["current_run_rate"] == 0), "run_rate_pressure"] = np.nan


def main():
    # --- Step 1: Parse all JSON files ---
    # parse_all() loops over every JSON in data/raw/, flattens each match
    # into rows, and returns two DataFrames. It also saves a first draft of
    # the CSVs — but we overwrite deliveries.csv below after fixing names.
    print("Step 1: Parsing raw JSON files...")
    deliveries_df, matches_df = parse_all()

    # --- Step 2: Standardise player names ---
    # Cricsheet spells the same player differently across seasons
    # (e.g. "V Kohli" vs "Virat Kohli"). build_name_map() reads every
    # JSON's registry block and picks the most-common spelling as canonical.
    print("\nStep 2: Standardising player names...")
    name_map = build_name_map()
    apply_to_deliveries(deliveries_df, name_map)
    print(f"  Name map built: {len(name_map)} entries")

    # --- Step 3: Add run-rate columns ---
    # These three columns are not in the raw JSON — they must be computed
    # from the flattened data. We do this here (not in the parser) to keep
    # parser.py focused on JSON → rows, and feature engineering here.
    print("\nStep 3: Adding run-rate columns...")
    add_run_rate_columns(deliveries_df)
    print("  Added: current_run_rate, required_run_rate, run_rate_pressure")

    # --- Step 4: Save the corrected deliveries CSV ---
    # matches_df has no player name columns, so it doesn't need re-saving.
    # deliveries_df now has corrected names + run-rate columns, so we
    # overwrite the file that parse_all() wrote in Step 1.
    print("\nStep 4: Saving corrected deliveries CSV...")
    deliveries_df.to_csv(PROCESSED_DIR / "deliveries.csv", index=False)
    print(f"  Saved → data/processed/deliveries.csv  ({len(deliveries_df):,} rows)")

    print("\nPipeline complete. All CSVs are ready in data/processed/")


if __name__ == "__main__":
    main()
