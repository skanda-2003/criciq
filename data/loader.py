from pathlib import Path
import pandas as pd

# Path to data/processed/ relative to this file - works regardless of where the app is run from
_PROCESSED = Path(__file__).parent / "processed"

# Load both heavy DataFrames once at import time.
# Python caches this module in sys.modules, so every page that does
# `from data.loader import DEL` gets the same object - no re-reading from disk.
DEL = pd.read_csv(_PROCESSED / "deliveries.csv")
MAT = pd.read_csv(_PROCESSED / "matches.csv")

# Cast all boolean flag columns once here so every page gets real bool dtype
# and never needs .astype(bool) again. Pandas reads 0/1 CSV columns as int64;
# casting here means filters like ~DEL["is_wide"] and DEL["wicket"] work directly.
_BOOL_COLS = ["super_over", "is_wide", "is_noball", "is_boundary_4", "is_boundary_6",
              "is_dot", "wicket"]
for _col in _BOOL_COLS:
    if _col in DEL.columns:
        DEL[_col] = DEL[_col].astype(bool)

# Convert high-cardinality string columns to category dtype - same value repeated
# thousands of times (e.g. "powerplay" across 100k rows) as Python string objects
# uses ~80 bytes each; category stores it once and uses a 2-byte integer per row.
# Saves ~250MB of RAM at startup, which matters on memory-constrained free hosting.
_CAT_COLS = [
    "venue", "city", "batting_team", "bowling_team",
    "batter", "non_striker", "bowler", "phase",
    "wicket_kind", "match_winner", "player_out",
]
for _col in _CAT_COLS:
    if _col in DEL.columns:
        DEL[_col] = DEL[_col].astype("category")
