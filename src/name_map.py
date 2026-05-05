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
    # A
    "A Badoni": "Ayush Badoni",
    "A Kamboj": "Anshul Kamboj",
    "A Manohar": "Atharva Manohar",
    "A Mhatre": "Ayush Mhatre",
    "A Mishra": "Amit Mishra",
    "A Nortje": "Anrich Nortje",
    "A Raghuvanshi": "Ankrish Raghuvanshi",
    "A Tomar": "Abhijeet Tomar",
    "A Zampa": "Adam Zampa",
    "AA Kulkarni": "Arshin Kulkarni",
    "AB de Villiers": "AB de Villiers",
    "AD Russell": "Andre Russell",
    "AF Milne": "Adam Milne",
    "AJ Finch": "Aaron Finch",
    "AJ Hosein": "Akeal Hosein",
    "AJ Turner": "Ashton Turner",
    "AJ Tye": "Andrew Tye",
    "AK Markram": "Aiden Markram",
    "AM Ghazanfar": "Mohammad Ghazanfar",
    "AM Rahane": "Ajinkya Rahane",
    "AR Patel": "Axar Patel",
    "AS Joseph": "Alzarri Joseph",
    "AS Roy": "Anukul Roy",
    "AT Rayudu": "Ambati Rayudu",
    "AU Rashid": "Adil Rashid",
    # B
    "B Indrajith": "Baba Indrajith",
    "B Kumar": "Bhuvneshwar Kumar",
    "B Muzarabani": "Blessing Muzarabani",
    "B Sai Sudharsan": "B Sai Sudharsan",
    "BA Stokes": "Ben Stokes",
    "BKG Mendis": "Kamindu Mendis",
    # C
    "C Bosch": "Corbin Bosch",
    "C Connolly": "Cooper Connolly",
    "C Green": "Cameron Green",
    "C Sakariya": "Chetan Sakariya",
    "CA Lynn": "Chris Lynn",
    "CH Gayle": "Chris Gayle",
    "CH Morris": "Chris Morris",
    "CJ Jordan": "Chris Jordan",
    "CR Woakes": "Chris Woakes",
    "CV Varun": "Varun Chakravarthy",
    # D
    "D Brevis": "Dewald Brevis",
    "D Ferreira": "Donovan Ferreira",
    "D Jansen": "Duan Jansen",
    "D Madushanka": "Dilshan Madushanka",
    "D Padikkal": "Devdutt Padikkal",
    "D Pretorius": "Dwaine Pretorius",
    "D Wiese": "David Wiese",
    "DA Miller": "David Miller",
    "DA Payne": "David Payne",
    "DA Warner": "David Warner",
    "DG Nalkande": "Darshan Nalkande",
    "DJ Bravo": "Dwayne Bravo",
    "DJ Hooda": "Deepak Hooda",
    "DJ Malan": "Dawid Malan",
    "DJ Mitchell": "Daryl Mitchell",
    "DJ Willey": "David Willey",
    "DL Chahar": "Deepak Chahar",
    "DP Conway": "Devon Conway",
    "DR Sams": "Daniel Sams",
    "DS Kulkarni": "Dhawal Kulkarni",
    "DS Rathi": "Digvesh Rathi",
    "DT Christian": "Dan Christian",
    # E
    "E Lewis": "Evin Lewis",
    "E Malinga": "Eshan Malinga",
    "EJG Morgan": "Eoin Morgan",
    # F
    "F du Plessis": "Faf du Plessis",
    "FA Allen": "Fabian Allen",
    "FH Allen": "Finn Allen",
    # G
    "G Coetzee": "Gerald Coetzee",
    "GD Phillips": "Glenn Phillips",
    "GF Linde": "George Linde",
    "GHS Garton": "George Garton",
    "GJ Maxwell": "Glenn Maxwell",
    # H
    "H Klaasen": "Heinrich Klaasen",
    "HC Brook": "Harry Brook",
    "HE van der Dussen": "Rassie van der Dussen",
    "HH Pandya": "Hardik Pandya",
    "HR Shokeen": "Hrithik Shokeen",
    "HV Patel": "Harshal Patel",
    # I
    "I Sharma": "Ishant Sharma",
    "IC Porel": "Ishan Porel",
    # J
    "J Fraser-McGurk": "Jake Fraser-McGurk",
    "J Little": "Josh Little",
    "J Overton": "Jamie Overton",
    "J Suchith": "Jagadeesha Suchith",
    "J Yadav": "Jayant Yadav",
    "JA Duffy": "Jacob Duffy",
    "JA Richardson": "Jhye Richardson",
    "JC Archer": "Jofra Archer",
    "JC Buttler": "Jos Buttler",
    "JD Unadkat": "Jaydev Unadkat",
    "JDS Neesham": "Jimmy Neesham",
    "JE Root": "Joe Root",
    "JG Bethell": "Jacob Bethell",
    "JJ Bumrah": "Jasprit Bumrah",
    "JJ Roy": "Jason Roy",
    "JM Bairstow": "Jonny Bairstow",
    "JM Sharma": "Jitesh Sharma",
    "JO Holder": "Jason Holder",
    "JP Behrendorff": "Jason Behrendorff",
    "JP Inglis": "Josh Inglis",
    "JR Hazlewood": "Josh Hazlewood",
    # K
    "K Gowtham": "Krishnappa Gowtham",
    "K Kartikeya": "Kumar Kartikeya",
    "K Khejroliya": "Kuldeep Khejroliya",
    "K Rabada": "Kagiso Rabada",
    "K Yadav": "Kuldeep Yadav",
    "KA Jamieson": "Kyle Jamieson",
    "KA Maharaj": "Keshav Maharaj",
    "KA Pollard": "Kieron Pollard",
    "KD Karthik": "Dinesh Karthik",
    "KH Pandya": "Krunal Pandya",
    "KK Ahmed": "Khaleel Ahmed",
    "KK Nair": "Karun Nair",
    "KL Nagarkoti": "Kamlesh Nagarkoti",
    "KL Rahul": "KL Rahul",
    "KM Asif": "KM Asif",
    "KM Jadhav": "Kedar Jadhav",
    "KR Mayers": "Kyle Mayers",
    "KR Sen": "Kuldeep Sen",
    "KS Bharat": "KS Bharat",
    "KS Rathore": "Kunal Singh Rathore",
    "KS Sharma": "Kartik Sharma",
    "KS Williamson": "Kane Williamson",
    "KT Maphaka": "Kwena Maphaka",
    "KV Sharma": "Karn Sharma",
    "KW Richardson": "Kane Richardson",
    # L
    "L Ngidi": "Lungi Ngidi",
    "L Wood": "Luke Wood",
    "LB Williams": "Lizaad Williams",
    "LH Ferguson": "Lockie Ferguson",
    "LS Livingstone": "Liam Livingstone",
    # M
    "M Ashwin": "Murugan Ashwin",
    "M Jansen": "Marco Jansen",
    "M Markande": "Mayank Markande",
    "M Pathirana": "Matheesha Pathirana",
    "M Prasidh Krishna": "Prasidh Krishna",
    "M Shahrukh Khan": "M Shahrukh Khan",
    "M Siddharth": "M Siddharth",
    "M Theekshana": "Maheesh Theekshana",
    "M Tiwari": "Manoj Tiwari",
    "M Vohra": "Manan Vohra",
    "MA Agarwal": "Mayank Agarwal",
    "MA Starc": "Mitchell Starc",
    "MA Wood": "Mark Wood",
    "MC Henriques": "Moises Henriques",
    "MD Choudhary": "Mukesh Choudhary",
    "MD Shanaka": "Dasun Shanaka",
    "MG Bracewell": "Michael Bracewell",
    "MJ Henry": "Matt Henry",
    "MJ Santner": "Mitchell Santner",
    "MJ Suthar": "Manav Suthar",
    "MK Lomror": "Mahipal Lomror",
    "MK Pandey": "Manish Pandey",
    "MM Ali": "Moeen Ali",
    "MM Sharma": "Mohit Sharma",
    "MP Stoinis": "Marcus Stoinis",
    "MP Yadav": "Mayank Yadav",
    "MR Marsh": "Mitchell Marsh",
    "MS Dhoni": "MS Dhoni",
    "MS Wade": "Matthew Wade",
    "MW Short": "Matt Short",
    # N
    "N Burger": "Nandre Burger",
    "N Jagadeesan": "Narayan Jagadeesan",
    "N Pooran": "Nicholas Pooran",
    "N Rana": "Nitish Rana",
    "N Thushara": "Nuwan Thushara",
    "N Wadhera": "Nishant Wadhera",
    "NM Coulter-Nile": "Nathan Coulter-Nile",
    "NT Ellis": "Nathan Ellis",
    # O
    "OC McCoy": "Obed McCoy",
    "OF Smith": "Odean Smith",
    # P
    "P Dubey": "Parth Dubey",
    "P Nissanka": "Pathum Nissanka",
    "P Simran Singh": "Prabhsimran Singh",
    "PBB Rajapaksa": "Bhanuka Rajapaksa",
    "PD Salt": "Phil Salt",
    "PH Solanki": "Prashant Solanki",
    "PHKD Mendis": "Kusal Mendis",
    "PJ Cummins": "Pat Cummins",
    "PJ Sangwan": "Pradeep Sangwan",
    "PK Garg": "Priyam Garg",
    "PN Mankad": "Priyank Mankad",
    "PP Chawla": "Piyush Chawla",
    "PP Hinge": "Praful Hinge",
    "PP Shaw": "Prithvi Shaw",
    "PR Veer": "Prashant Veer",
    "PVD Chameera": "Dushmantha Chameera",
    "PWA Mulder": "Wiaan Mulder",
    "PWH de Silva": "Wanindu Hasaranga",
    # Q
    "Q de Kock": "Quinton de Kock",
    # R
    "R Ashwin": "Ravichandran Ashwin",
    "R Dhawan": "Rishi Dhawan",
    "R Goyal": "Raghav Goyal",
    "R Minz": "Robin Minz",
    "R Parag": "Riyan Parag",
    "R Powell": "Rovman Powell",
    "R Ravindra": "Rachin Ravindra",
    "R Sai Kishore": "R Sai Kishore",
    "R Shepherd": "Romario Shepherd",
    "R Tewatia": "Rahul Tewatia",
    "RA Bawa": "Raj Angad Bawa",
    "RA Jadeja": "Ravindra Jadeja",
    "RA Tripathi": "Rahul Tripathi",
    "RD Chahar": "Deepak Chahar",
    "RD Gaikwad": "Ruturaj Gaikwad",
    "RD Rickelton": "Ryan Rickelton",
    "RG Sharma": "Rohit Sharma",
    "RJ Gleeson": "Richard Gleeson",
    "RJW Topley": "Reece Topley",
    "RK Bhui": "Ricky Bhui",
    "RK Singh": "Rinku Singh",
    "RM Patidar": "Rajat Patidar",
    "RP Meredith": "Riley Meredith",
    "RR Pant": "Rishabh Pant",
    "RR Rossouw": "Rilee Rossouw",
    "RS Hangargekar": "Rajvardhan Hangargekar",
    "RV Patel": "Ripal Patel",
    "RV Uthappa": "Robin Uthappa",
    # S
    "S Arora": "Salil Arora",
    "S Dhawan": "Shikhar Dhawan",
    "S Dube": "Shivam Dube",
    "S Gopal": "Shreyas Gopal",
    "S Joseph": "Shamar Joseph",
    "S Kaul": "Siddarth Kaul",
    "S Nadeem": "Shahbaz Nadeem",
    "S Sandeep Warrier": "Sandeep Warrier",
    "SA Abbott": "Sean Abbott",
    "SA Yadav": "Suryakumar Yadav",
    "SB Dubey": "Saurabh Dubey",
    "SD Hope": "Shai Hope",
    "SE Rutherford": "Shimron Rutherford",
    "SH Johnson": "Spencer Johnson",
    "SK Raina": "Suresh Raina",
    "SK Rasheed": "Shaik Rasheed",
    "SM Curran": "Sam Curran",
    "SN Khan": "Sarfaraz Khan",
    "SN Thakur": "Shardul Thakur",
    "SO Hetmyer": "Shimron Hetmyer",
    "SP Jackson": "Sheldon Jackson",
    "SP Narine": "Sunil Narine",
    "SPD Smith": "Steve Smith",
    "SS Iyer": "Shreyas Iyer",
    "SS Prabhudessai": "Suyash Prabhudessai",
    "SS Tiwary": "Saurabh Tiwary",
    "SSB Magala": "Sisanda Magala",
    "SV Samson": "Sanju Samson",
    "SW Billings": "Sam Billings",
    "SZ Mulani": "Shams Mulani",
    # T
    "T Kohler-Cadmore": "Tom Kohler-Cadmore",
    "T Natarajan": "Thangarasu Natarajan",
    "T Shamsi": "Tabraiz Shamsi",
    "T Stubbs": "Tristan Stubbs",
    "TA Boult": "Trent Boult",
    "TG Southee": "Tim Southee",
    "TH David": "Tim David",
    "TK Curran": "Tom Curran",
    "TL Seifert": "Tim Seifert",
    "TM Head": "Travis Head",
    "TS Mills": "Tymal Mills",
    "TU Deshpande": "Tushar Deshpande",
    # U
    "UT Yadav": "Umesh Yadav",
    # V
    "V Kaverappa": "Vidwath Kaverappa",
    "V Kohli": "Virat Kohli",
    "V Nigam": "Vipraj Nigam",
    "V Puthur": "Vignesh Puthur",
    "V Shankar": "Vijay Shankar",
    "V Suryavanshi": "Vaibhav Suryavanshi",
    "V Viyaskanth": "Vijayakanth Viyaskanth",
    "VG Arora": "Vaibhav Arora",
    "VR Aaron": "Varun Aaron",
    "VR Iyer": "Venkatesh Iyer",
    # W
    "W O'Rourke": "Will O'Rourke",
    "WD Parnell": "Wayne Parnell",
    "WG Jacks": "Will Jacks",
    "WP Saha": "Wriddhiman Saha",
    # X
    "XC Bartlett": "Xavier Bartlett",
    # Y
    "YBK Jaiswal": "Yashasvi Jaiswal",
    "YS Chahal": "Yuzvendra Chahal",
    "YV Dhull": "Yash Dhull",
}


def get_full_name(short: str) -> str:
    # returns the display-friendly full name, or the original string if not in the dict
    return FULL_NAMES.get(short, short)
