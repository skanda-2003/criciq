# Shared constants used across multiple page files.
# Import from here - never redefine locally.

# Wicket kinds that are credited to the bowler.
# Run-outs, retired hurt, obstructing the field, etc. are excluded.
BOWLER_WICKET_KINDS = {"caught", "bowled", "lbw", "caught and bowled", "stumped", "hit wicket"}

# Franchise renames - maps old Cricsheet names to current canonical names.
# Applied wherever DEL or MAT are filtered by team so historical matches
# from old-name eras are included under the current franchise name.
TEAM_RENAME = {
    "Royal Challengers Bangalore": "Royal Challengers Bengaluru",
    "Rising Pune Supergiant":      "Rising Pune Supergiants",
    "Delhi Daredevils":            "Delhi Capitals",
    "Kings XI Punjab":             "Punjab Kings",
}
