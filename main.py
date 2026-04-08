"""
Main pipeline for CricIQ.

Run this file once to generate the processed CSVs:
    python main.py

It does three things in order:
  1. Parse all raw JSON files → deliveries_df and matches_df
  2. Standardise player names across seasons using the name map
  3. Save the final DataFrames to data/processed/
"""

from pathlib import Path

from src.parser import parse_all
from src.name_map import build_name_map, apply_to_deliveries


PROCESSED_DIR = Path("data/processed")


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

    # --- Step 3: Save the corrected deliveries CSV ---
    # matches_df has no player name columns, so it doesn't need re-saving.
    # deliveries_df now has corrected batter/bowler/player_out names, so
    # we overwrite the file that parse_all() wrote in Step 1.
    print("\nStep 3: Saving corrected deliveries CSV...")
    deliveries_df.to_csv(PROCESSED_DIR / "deliveries.csv", index=False)
    print(f"  Saved → data/processed/deliveries.csv  ({len(deliveries_df):,} rows)")

    print("\nPipeline complete. Both CSVs are ready in data/processed/")


if __name__ == "__main__":
    main()
