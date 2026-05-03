from pathlib import Path
import pandas as pd

# Path to data/processed/ relative to this file - works regardless of where the app is run from
_PROCESSED = Path(__file__).parent / "processed"

# Load both heavy DataFrames once at import time.
# Python caches this module in sys.modules, so every page that does
# `from data.loader import DEL` gets the same object - no re-reading from disk.
DEL = pd.read_csv(_PROCESSED / "deliveries.csv")
MAT = pd.read_csv(_PROCESSED / "matches.csv")
