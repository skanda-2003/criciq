# main pipeline for CricIQ
# run this file once to generate the processed CSVs:
#     python main.py
#
# does four things in order:
#   1. parse all raw JSON files into deliveries_df and matches_df
#   2. standardise player names across seasons using the name map
#   3. add run-rate columns needed by the win probability model
#   4. save the final DataFrames to data/processed/

from pathlib import Path

import numpy as np

from src.parser import parse_all
from src.name_map import build_name_map, apply_to_deliveries


PROCESSED_DIR = Path("data/processed")

# total overs in an IPL innings, used when computing overs remaining
TOTAL_OVERS = 20


def add_run_rate_columns(df):
    # adds current_run_rate, required_run_rate and run_rate_pressure to the deliveries DataFrame
    # these three columns are needed by the win probability model (Angle 4)
    # computed from columns that already exist after parsing: over, ball_in_over,
    # cumulative_runs, target_runs and innings

    # overs_completed: how many full overs have been bowled at the end of this delivery
    # over is 1-indexed and ball_in_over counts only legal deliveries (1-6)
    # (over - 1) captures completed overs before the current one
    # adding ball_in_over / 6 gives fractional credit for the current over
    # e.g. over=3, ball_in_over=3 means 2 + 0.5 = 2.5 overs completed
    # wides and no-balls have ball_in_over=0 so they don't advance the over count
    overs_completed = (df["over"] - 1) + (df["ball_in_over"] / 6)

    # current_run_rate: runs scored so far divided by overs completed
    # NaN when overs_completed is 0 (the very first delivery) to avoid dividing by zero
    crr = df["cumulative_runs"] / overs_completed
    crr[overs_completed == 0] = np.nan
    df["current_run_rate"] = crr

    # required_run_rate: runs still needed divided by overs remaining, second innings only
    # target_runs is NaN for first innings rows so the result is automatically NaN there
    overs_remaining = TOTAL_OVERS - overs_completed
    runs_needed = df["target_runs"] - df["cumulative_runs"]

    rrr = runs_needed / overs_remaining
    rrr[overs_remaining == 0] = np.nan   # end of innings, no overs left
    rrr[runs_needed <= 0] = np.nan       # target already reached or passed
    rrr = rrr.clip(upper=36)
    df["required_run_rate"] = rrr

    # run_rate_pressure: required rate divided by current rate
    # a value above 1 means the team needs to score faster than they currently are
    # e.g. 2.0 means they need to double their current scoring rate to win
    # NaN wherever either CRR or RRR is NaN (first innings and very start of second)
    df["run_rate_pressure"] = df["required_run_rate"] / df["current_run_rate"]
    df.loc[df["current_run_rate"].isnull() | (df["current_run_rate"] == 0), "run_rate_pressure"] = np.nan


def main():
    # step 1: parse all JSON files
    # parse_all loops over every JSON in data/raw/, flattens each match into rows
    # and returns two DataFrames. also saves a first draft of the CSVs which I
    # overwrite below after fixing the names
    print("Step 1: Parsing raw JSON files...")
    deliveries_df, matches_df = parse_all()

    # step 2: standardise player names
    # Cricsheet spells the same player differently across seasons
    # e.g. "V Kohli" vs "Virat Kohli". build_name_map reads every JSON's registry
    # block and picks the most common spelling as the canonical one
    print("\nStep 2: Standardising player names...")
    name_map = build_name_map()
    apply_to_deliveries(deliveries_df, name_map)
    print(f"  Name map built: {len(name_map)} entries")

    # step 3: add run-rate columns
    # these are not in the raw JSON so I compute them here from the flattened data
    # doing this in main.py rather than parser.py keeps the parser focused on JSON to rows
    print("\nStep 3: Adding run-rate columns...")
    add_run_rate_columns(deliveries_df)
    print("  Added: current_run_rate, required_run_rate, run_rate_pressure")

    # step 4: save the corrected deliveries CSV
    # matches_df has no player name columns so it doesn't need re-saving
    # deliveries_df now has corrected names and run-rate columns so I overwrite
    # the file that parse_all wrote in step 1
    print("\nStep 4: Saving corrected deliveries CSV...")
    deliveries_df.to_csv(PROCESSED_DIR / "deliveries.csv", index=False)
    print(f"  Saved -> data/processed/deliveries.csv  ({len(deliveries_df):,} rows)")

    print("\nPipeline complete. All CSVs are ready in data/processed/")


if __name__ == "__main__":
    main()
