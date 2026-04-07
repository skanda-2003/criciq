"""
Player name standardisation for CricIQ.

Cricsheet's registry maps every name string to a unique player ID.
Where the same player ID appears under multiple name strings across
seasons, we normalise to the most-frequently-used (canonical) form.

Usage
-----
    from src.name_map import build_name_map, standardise

    name_map = build_name_map()          # call once
    df["batter"] = df["batter"].map(lambda n: standardise(n, name_map))
"""

import json
from collections import defaultdict
from pathlib import Path

RAW_DIR = Path(__file__).parent.parent / "data" / "raw"


def build_name_map(raw_dir: Path = RAW_DIR) -> dict[str, str]:
    """Return a dict mapping every known alias → canonical player name.

    The canonical name is whichever spelling appeared most often across
    all Cricsheet registry entries for that player ID.

    Players with only one known spelling map to themselves, so the dict
    is safe to apply unconditionally (unknown names pass through unchanged
    when you use `name_map.get(name, name)`).
    """
    # Step 1: accumulate (id -> {name: count}) from all registry blocks
    id_to_freq: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))

    for path in raw_dir.glob("*.json"):
        try:
            data = json.loads(path.read_text())
        except Exception:
            continue
        registry = data.get("info", {}).get("registry", {}).get("people", {})
        for name, pid in registry.items():
            id_to_freq[pid][name] += 1

    # Step 2: for each player ID, pick the most-frequent name as canonical
    name_map: dict[str, str] = {}
    for pid, freq in id_to_freq.items():
        canonical = max(freq, key=freq.__getitem__)
        for alias in freq:
            name_map[alias] = canonical

    return name_map


def standardise(name: str | None, name_map: dict[str, str]) -> str | None:
    """Return the canonical form of `name`, or the original if not in the map."""
    if name is None:
        return None
    return name_map.get(name, name)


def apply_to_deliveries(df, name_map: dict[str, str]):
    """Standardise all player-name columns in the deliveries DataFrame in-place."""
    player_cols = ["batter", "non_striker", "bowler", "player_out"]
    for col in player_cols:
        if col in df.columns:
            df[col] = df[col].map(lambda n: standardise(n, name_map))
    return df


if __name__ == "__main__":
    name_map = build_name_map()

    # Report only aliases that differ from their canonical form
    aliases = {alias: canon for alias, canon in name_map.items() if alias != canon}
    print(f"Name map built: {len(name_map)} entries, {len(aliases)} aliases resolved")
    for alias, canon in sorted(aliases.items()):
        print(f"  '{alias}'  →  '{canon}'")
