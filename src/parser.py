"""
Cricsheet IPL JSON parser.
Flattens nested match JSON files into two DataFrames:
  - deliveries.csv : one row per ball
  - matches.csv    : one row per match
"""

import json
from pathlib import Path

import pandas as pd
from tqdm import tqdm


RAW_DIR = Path(__file__).parent.parent / "data" / "raw"
PROCESSED_DIR = Path(__file__).parent.parent / "data" / "processed"


def parse_match(path: Path) -> tuple[list[dict], dict | None]:
    """Parse a single Cricsheet JSON file.

    Returns (deliveries, match_info) where deliveries is a list of dicts
    (one per ball) and match_info is a single dict for the match summary.
    Returns ([], None) on parse error.
    """
    try:
        with open(path) as f:
            data = json.load(f)
    except Exception:
        return [], None

    info = data.get("info", {})
    match_id = path.stem

    # --- match-level fields ---
    teams = info.get("teams", [None, None])
    outcome = info.get("outcome", {})
    winner = outcome.get("winner")
    result = "no result"
    if winner:
        result = "normal"
    elif "bowl_out" in outcome:
        result = "bowl_out"
    elif outcome.get("result") == "tie":
        result = "tie"

    toss = info.get("toss", {})
    dates = info.get("dates", [])
    # Extract year from the match date (format: "YYYY-MM-DD") rather than
    # using the JSON's season field, which can be "2007/08" style strings.
    # Falls back to the season field only if no date is available.
    if dates:
        season = str(dates[0])[:4]   # e.g. "2008-04-18" → "2008"
    else:
        season = str(info.get("season", "unknown"))

    match_info = {
        "match_id": match_id,
        "season": season,
        "date": dates[0] if dates else None,
        "venue": info.get("venue"),
        "city": info.get("city"),
        "team1": teams[0] if len(teams) > 0 else None,
        "team2": teams[1] if len(teams) > 1 else None,
        "toss_winner": toss.get("winner"),
        "toss_decision": toss.get("decision"),
        "winner": winner,
        "result": result,
        "result_margin_runs": outcome.get("by", {}).get("runs"),
        "result_margin_wickets": outcome.get("by", {}).get("wickets"),
        "player_of_match": ", ".join(info.get("player_of_match", [])),
    }

    # --- delivery-level fields ---
    deliveries = []
    for innings_idx, innings in enumerate(data.get("innings", []), start=1):
        batting_team = innings.get("team")
        is_super_over = innings.get("super_over", False)
        target_info = innings.get("target", {})
        target_runs = target_info.get("runs")    # None for innings 1 (no target yet)
        target_overs = target_info.get("overs")  # None for innings 1
        batting_order = {}
        next_position = 1
        bowling_team = next(
            (t for t in teams if t != batting_team), None
        )

        # running totals for cumulative run / wicket tracking
        cumulative_runs = 0
        cumulative_wickets = 0

        for over_data in innings.get("overs", []):
            over_num = over_data.get("over", 0)  # 0-indexed in Cricsheet
            legal_ball_num = 0  # counts only legal deliveries within the over

            for ball_data in over_data.get("deliveries", []):
                runs = ball_data.get("runs", {})
                extras = ball_data.get("extras", {})
                wickets = ball_data.get("wickets", [])

                batter_runs = runs.get("batter", 0)
                extra_runs = runs.get("extras", 0)
                total_runs = runs.get("total", 0)

                is_wide = "wides" in extras
                is_noball = "noballs" in extras
                is_legal = not (is_wide or is_noball)
                if is_legal:
                    legal_ball_num += 1

                is_boundary_4 = batter_runs == 4
                is_boundary_6 = batter_runs == 6
                is_dot = batter_runs == 0 and not extras

                wicket_kind = wickets[0].get("kind") if wickets else None
                player_out = wickets[0].get("player_out") if wickets else None
                # fielders involved (catches, run-outs)
                fielders = (
                    ", ".join(
                        f.get("name", "") for f in wickets[0].get("fielders", [])
                    )
                    if wickets
                    else None
                )

                # phase: powerplay 1-6, middle 7-15, death 16-20 (1-indexed over)
                over_1idx = over_num + 1
                if over_1idx <= 6:
                    phase = "powerplay"
                elif over_1idx <= 15:
                    phase = "middle"
                else:
                    phase = "death"

                cumulative_runs += total_runs
                cumulative_wickets += len(wickets)

                batter_name = ball_data.get("batter")
                if batter_name not in batting_order:                   
                    batting_order[batter_name] = next_position
                    next_position += 1                                 
                batter_pos = batting_order[batter_name]
                
                deliveries.append(
                    {
                        "match_id": match_id,
                        "season": season,
                        "venue": info.get("venue"),
                        "city": info.get("city"),
                        "innings": innings_idx,
                        "batting_team": batting_team,
                        "bowling_team": bowling_team,
                        "over": over_1idx,          # 1-indexed
                        "ball_in_over": legal_ball_num,
                        "batter": ball_data.get("batter"),
                        "non_striker": ball_data.get("non_striker"),
                        "bowler": ball_data.get("bowler"),
                        "batting_position": batter_pos,
                        "target_runs": target_runs,
                        "target_overs": target_overs,
                        "super_over": is_super_over,
                        "batter_runs": batter_runs,
                        "extra_runs": extra_runs,
                        "total_runs": total_runs,
                        "is_wide": is_wide,
                        "is_noball": is_noball,
                        "is_boundary_4": is_boundary_4,
                        "is_boundary_6": is_boundary_6,
                        "is_dot": is_dot,
                        "wicket": len(wickets) > 0,
                        "wicket_kind": wicket_kind,
                        "player_out": player_out,
                        "fielders": fielders,
                        "phase": phase,
                        "cumulative_runs": cumulative_runs,
                        "cumulative_wickets": cumulative_wickets,
                        "match_winner": winner,
                    }
                )

    return deliveries, match_info


def parse_all(raw_dir: Path = RAW_DIR, processed_dir: Path = PROCESSED_DIR):
    json_files = sorted(raw_dir.glob("*.json"))
    print(f"Found {len(json_files)} JSON files in {raw_dir}")

    all_deliveries = []
    all_matches = []
    errors = []

    for path in tqdm(json_files, desc="Parsing matches"):
        deliveries, match_info = parse_match(path)
        if match_info is None:
            errors.append(path.name)
            continue
        all_deliveries.extend(deliveries)
        all_matches.append(match_info)

    if errors:
        print(f"Skipped {len(errors)} files due to parse errors: {errors[:5]}")

    deliveries_df = pd.DataFrame(all_deliveries)
    matches_df = pd.DataFrame(all_matches)

    # lightweight type fixes
    for col in ["is_wide", "is_noball", "is_boundary_4", "is_boundary_6", "is_dot", "wicket", "super_over"]:
        deliveries_df[col] = deliveries_df[col].astype(bool)

    processed_dir.mkdir(parents=True, exist_ok=True)
    deliveries_df.to_csv(processed_dir / "deliveries.csv", index=False)
    matches_df.to_csv(processed_dir / "matches.csv", index=False)

    print(f"\nDone.")
    print(f"  deliveries : {len(deliveries_df):,} rows  → data/processed/deliveries.csv")
    print(f"  matches    : {len(matches_df):,} rows  → data/processed/matches.csv")
    return deliveries_df, matches_df


if __name__ == "__main__":
    parse_all()
