# player name standardisation for CricIQ
#
# Cricsheet's registry maps every name string to a unique player ID
# where the same player ID appears under multiple name strings across seasons,
# we normalise to the most frequently used (canonical) form
#
# usage:
#     from src.name_map import build_name_map, standardise
#     name_map = build_name_map()
#     df["batter"] = df["batter"].map(lambda n: standardise(n, name_map))

import json
from collections import defaultdict
from pathlib import Path

RAW_DIR = Path(__file__).parent.parent / "data" / "raw"


def build_name_map(raw_dir: Path = RAW_DIR) -> dict[str, str]:
    # returns a dict mapping every known alias to the canonical player name
    # canonical = whichever spelling appeared most often across all registry entries for that player ID
    # players with only one known spelling map to themselves, so the dict is safe to apply
    # unconditionally (unknown names pass through unchanged with name_map.get(name, name))

    # step 1: build (id -> {name: count}) from all registry blocks
    id_to_freq: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))

    for path in raw_dir.glob("*.json"):
        try:
            data = json.loads(path.read_text())
        except Exception:
            continue
        registry = data.get("info", {}).get("registry", {}).get("people", {})
        for name, pid in registry.items():
            id_to_freq[pid][name] += 1

    # step 2: for each player ID, pick the most frequent name as canonical
    name_map: dict[str, str] = {}
    for pid, freq in id_to_freq.items():
        canonical = max(freq, key=freq.__getitem__)
        for alias in freq:
            name_map[alias] = canonical

    return name_map


def standardise(name: str | None, name_map: dict[str, str]) -> str | None:
    # returns the canonical form of name, or the original string if not in the map
    if name is None:
        return None
    return name_map.get(name, name)


def apply_to_deliveries(df, name_map: dict[str, str]):
    # standardise all player name columns in the deliveries DataFrame in-place
    player_cols = ["batter", "non_striker", "bowler", "player_out"]
    for col in player_cols:
        if col in df.columns:
            df[col] = df[col].map(lambda n: standardise(n, name_map))
    return df


if __name__ == "__main__":
    name_map = build_name_map()

    # only show entries where the alias differs from the canonical name
    aliases = {alias: canon for alias, canon in name_map.items() if alias != canon}
    print(f"Name map built: {len(name_map)} entries, {len(aliases)} aliases resolved")
    for alias, canon in sorted(aliases.items()):
        print(f"  '{alias}'  ->  '{canon}'")


# Cricsheet stores player names in abbreviated form (e.g. "V Kohli", "RG Sharma").
# This dict maps those abbreviations to the full display name used in the dashboard.
# Import get_full_name() in any page that needs to show player names in a dropdown or label.
FULL_NAMES: dict[str, str] = {
    "A Badoni": "Ayush Badoni",
    "A Manohar": "Atharva Manohar",
    "A Mhatre": "Angkrish Mhatre",
    "A Raghuvanshi": "Ayush Raghuvanshi",
    "AB de Villiers": "AB de Villiers",
    "AD Russell": "Andre Russell",
    "AK Markram": "Aiden Markram",
    "AM Rahane": "Ajinkya Rahane",
    "AR Patel": "Axar Patel",
    "AT Rayudu": "Ambati Rayudu",
    "B Kumar": "Bhuvneshwar Kumar",
    "B Sai Sudharsan": "B Sai Sudharsan",
    "C Green": "Cameron Green",
    "CH Gayle": "Chris Gayle",
    "D Brevis": "Dewald Brevis",
    "D Ferreira": "Donovan Ferreira",
    "D Padikkal": "Devdutt Padikkal",
    "DA Miller": "David Miller",
    "DA Warner": "David Warner",
    "DJ Hooda": "Deepak Hooda",
    "DJ Mitchell": "Daryl Mitchell",
    "DP Conway": "Devon Conway",
    "E Lewis": "Evin Lewis",
    "EJG Morgan": "Eoin Morgan",
    "F du Plessis": "Faf du Plessis",
    "GD Phillips": "Glenn Phillips",
    "GJ Maxwell": "Glenn Maxwell",
    "H Klaasen": "Heinrich Klaasen",
    "HC Brook": "Harry Brook",
    "HH Pandya": "Hardik Pandya",
    "HV Patel": "Harshal Patel",
    "J Fraser-McGurk": "Jake Fraser-McGurk",
    "J Overton": "Jamie Overton",
    "JC Buttler": "Jos Buttler",
    "JD Unadkat": "Jaydev Unadkat",
    "JG Bethell": "Jacob Bethell",
    "JJ Roy": "Jason Roy",
    "JM Bairstow": "Jonny Bairstow",
    "JM Sharma": "Mohit Sharma",
    "JO Holder": "Jason Holder",
    "JP Inglis": "Josh Inglis",
    "K Rabada": "Kagiso Rabada",
    "KA Pollard": "Kieron Pollard",
    "KD Karthik": "Dinesh Karthik",
    "KH Pandya": "Krunal Pandya",
    "KK Nair": "Karun Nair",
    "KL Rahul": "KL Rahul",
    "KR Mayers": "Kyle Mayers",
    "KS Bharat": "KS Bharat",
    "KS Williamson": "Kane Williamson",
    "LS Livingstone": "Liam Livingstone",
    "M Jansen": "Marco Jansen",
    "M Shahrukh Khan": "M Shahrukh Khan",
    "M Vohra": "Manan Vohra",
    "MA Agarwal": "Mayank Agarwal",
    "MD Choudhary": "Mukesh Choudhary",
    "MJ Santner": "Mitchell Santner",
    "MK Lomror": "Mahipal Lomror",
    "MK Pandey": "Manish Pandey",
    "MM Ali": "Moeen Ali",
    "MP Stoinis": "Marcus Stoinis",
    "MR Marsh": "Mitchell Marsh",
    "MS Dhoni": "MS Dhoni",
    "MS Wade": "Matthew Wade",
    "MW Short": "Matt Short",
    "N Jagadeesan": "Narayan Jagadeesan",
    "N Pooran": "Nicholas Pooran",
    "N Rana": "Nitish Rana",
    "N Wadhera": "Nishant Wadhera",
    "P Nissanka": "Pathum Nissanka",
    "PBB Rajapaksa": "Bhanuka Rajapaksa",
    "PD Salt": "Phil Salt",
    "PJ Cummins": "Pat Cummins",
    "PP Shaw": "Prithvi Shaw",
    "Q de Kock": "Quinton de Kock",
    "R Ashwin": "Ravichandran Ashwin",
    "R Parag": "Riyan Parag",
    "R Powell": "Rovman Powell",
    "R Ravindra": "Rachin Ravindra",
    "R Shepherd": "Romario Shepherd",
    "R Tewatia": "Rahul Tewatia",
    "RA Jadeja": "Ravindra Jadeja",
    "RK Singh": "Rinku Singh",
    "RA Tripathi": "Rahul Tripathi",
    "RD Chahar": "Deepak Chahar",
    "RD Gaikwad": "Ruturaj Gaikwad",
    "RD Rickelton": "Ryan Rickelton",
    "RG Sharma": "Rohit Sharma",
    "RM Patidar": "Rajat Patidar",
    "RR Pant": "Rishabh Pant",
    "RR Rossouw": "Rilee Rossouw",
    "RV Uthappa": "Robin Uthappa",
    "S Dhawan": "Shikhar Dhawan",
    "S Dube": "Shivam Dube",
    "SA Yadav": "Suryakumar Yadav",
    "SB Dubey": "Saurabh Dubey",
    "SD Hope": "Shai Hope",
    "SK Raina": "Suresh Raina",
    "SM Curran": "Sam Curran",
    "SN Thakur": "Shardul Thakur",
    "SO Hetmyer": "Shimron Hetmyer",
    "SP Narine": "Sunil Narine",
    "SPD Smith": "Steve Smith",
    "SS Iyer": "Shreyas Iyer",
    "SS Tiwary": "Saurabh Tiwary",
    "SV Samson": "Sanju Samson",
    "SW Billings": "Sam Billings",
    "T Kohler-Cadmore": "Tom Kohler-Cadmore",
    "T Stubbs": "Tristan Stubbs",
    "TA Boult": "Trent Boult",
    "TH David": "Tim David",
    "TM Head": "Travis Head",
    "UT Yadav": "Umesh Yadav",
    "V Kohli": "Virat Kohli",
    "V Shankar": "Vijay Shankar",
    "V Suryavanshi": "Vaibhav Suryavanshi",
    "VR Iyer": "Venkatesh Iyer",
    "WG Jacks": "Will Jacks",
    "WP Saha": "Wriddhiman Saha",
    "YBK Jaiswal": "Yashasvi Jaiswal",
}


def get_full_name(short: str) -> str:
    # returns the display-friendly full name, or the original string if not in the dict
    return FULL_NAMES.get(short, short)
