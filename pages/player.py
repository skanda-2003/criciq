import dash
from dash import html, dcc, callback, Input, Output
import dash_bootstrap_components as dbc
import pandas as pd
import plotly.graph_objects as go

from components.metric_card import metric_card
from components.charts import CHART_THEME

dash.register_page(__name__, path="/player", name="Player Deep-Dive", title="CricIQ - Player")

# ── Load data at server start ────────────────────────────────────────
_phase    = pd.read_csv("data/processed/phase_batting.csv")
_matchups = pd.read_csv("data/processed/bowler_matchups.csv")
_profiles = pd.read_csv("data/processed/batsman_profiles.csv")  # k-means cluster per batsman
_impact   = pd.read_csv("data/processed/player_impact_season.csv")  # season-level impact scores

# Cricsheet uses abbreviated names (e.g. "A Badoni") - this maps them to full names
# so the dropdown shows the full name and search works with either first name or surname
_FULL_NAMES = {
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

def _display_name(short: str) -> str:
    return _FULL_NAMES.get(short, short)

# Players with at least 50 balls in any single phase
_players = sorted(_phase[_phase["balls_faced"] >= 50]["batter"].unique())

PHASE_ORDER  = ["powerplay", "middle", "death"]
PHASE_COLORS = {"powerplay": "#3b82f6", "middle": "#22c55e", "death": "#f97316"}

# League average SR per phase - weighted (total runs / total balls * 100) across all 50+ ball qualifiers
# This is the "average qualified batsman" for each phase, used as a reference line
_LEAGUE_AVG_SR = {}
for _p in PHASE_ORDER:
    _pf = _phase[(_phase["phase"] == _p) & (_phase["balls_faced"] >= 50)]
    if not _pf.empty:
        _LEAGUE_AVG_SR[_p] = _pf["runs_scored"].sum() / _pf["balls_faced"].sum() * 100

# Cluster labels derived from inspecting the k-means output in notebook 03
# Cluster 0: high SR (~141), very low dismissal rate (~2.6%) - consistent and hard to dismiss
# Cluster 1: high SR (~143), high dismissal rate (~4.4%) - aggressive risk-takers
# Cluster 2: lower SR (~127), fewer boundaries - steady builders
# Cluster 3: very high SR (~169), very high boundary rate - pure power hitters
_CLUSTER_LABELS = {
    0: ("Consistent Striker", "#22c55e"),
    1: ("Aggressive Hitter",  "#f97316"),
    2: ("Steady Builder",     "#888888"),
    3: ("Power Hitter",       "#3b82f6"),
}

# ── Layout ───────────────────────────────────────────────────────────
layout = html.Div([

    html.Span("Player Deep-Dive · 2021–2026", className="section-label"),

    # Row 1: player dropdown + cluster badge (badge fills in via callback)
    dbc.Row([
        dbc.Col(
            dcc.Dropdown(
                id="player-select",
                # label shows full name, value stays as the Cricsheet abbreviated name
                # so searching "Ayush" or "Badoni" or "Ayush Badoni" all match "A Badoni"
                options=[{"label": _display_name(p), "value": p} for p in _players],
                value=_players[0],
                clearable=False,
                searchable=True,
            ),
            width=4,
        ),
        dbc.Col(
            html.Div(id="player-cluster-badge"),
            width="auto",
            className="d-flex align-items-center",
        ),
    ], className="card-row"),

    # Row 2: summary metric cards
    dbc.Row(id="player-metrics", className="card-row"),

    # Row 3: phase SR chart (with league avg reference) + matchup chart
    dbc.Row([
        dbc.Col(html.Div(id="player-phase-chart",   className="chart-card"), width=6),
        dbc.Col(html.Div(id="player-matchup-chart", className="chart-card"), width=6),
    ], className="card-row"),

    # Row 4: impact score trend across seasons
    dbc.Row([
        dbc.Col(html.Div(id="player-impact-chart", className="chart-card"), width=6),
    ], className="card-row"),

])


@callback(
    Output("player-metrics",       "children"),
    Output("player-phase-chart",   "children"),
    Output("player-matchup-chart", "children"),
    Output("player-cluster-badge", "children"),
    Output("player-impact-chart",  "children"),
    Input("player-select", "value"),
)
def update_player(player):
    df = _phase[_phase["batter"] == player]

    # ── Metric cards ─────────────────────────────────────────────────
    total_balls      = df["balls_faced"].sum()
    total_runs       = df["runs_scored"].sum()
    total_boundaries = df["boundaries"].sum()
    total_dots       = df["dots"].sum()

    sr   = round(total_runs / total_balls * 100, 1) if total_balls > 0 else 0
    bpct = round(total_boundaries / total_balls * 100, 1) if total_balls > 0 else 0
    dpct = round(total_dots / total_balls * 100, 1) if total_balls > 0 else 0

    metrics = [
        dbc.Col(metric_card("Strike Rate", str(sr),          progress=int(min(sr / 200 * 100, 100)),         color="blue"),   width=3),
        dbc.Col(metric_card("Balls Faced", str(total_balls), progress=int(min(total_balls / 500 * 100, 100)), color="green"),  width=3),
        dbc.Col(metric_card("Boundary %",  f"{bpct}%",       progress=int(min(bpct / 40 * 100, 100)),         color="orange"), width=3),
        dbc.Col(metric_card("Dot Ball %",  f"{dpct}%",       progress=int(dpct),                              color="red"),    width=3),
    ]

    # ── Phase SR chart with league average reference lines (E) ────────
    df_ph = df[df["phase"].isin(PHASE_ORDER)].set_index("phase").reindex(PHASE_ORDER).dropna()

    fig_phase = go.Figure()

    # Player's actual SR bars
    fig_phase.add_trace(go.Bar(
        x=df_ph["strike_rate"],
        y=df_ph.index,
        orientation="h",
        marker_color=[PHASE_COLORS[p] for p in df_ph.index],
        marker_line_width=0,
        width=0.5,
        text=[f"{v:.0f}" for v in df_ph["strike_rate"]],
        textposition="outside",
        textfont={"size": 10, "color": "#888"},
        showlegend=False,
    ))

    # League average markers - vertical tick at the league avg SR for each phase
    # This shows at a glance whether the player is above or below the typical qualified batsman
    for phase in df_ph.index:
        if phase in _LEAGUE_AVG_SR:
            fig_phase.add_trace(go.Scatter(
                x=[_LEAGUE_AVG_SR[phase]],
                y=[phase],
                mode="markers+text",
                marker=dict(symbol="line-ns-open", size=22, color="#ccc", line=dict(width=2, color="#ccc")),
                text=[f"avg {_LEAGUE_AVG_SR[phase]:.0f}"],
                textposition="bottom center",
                textfont=dict(size=9, color="#aaa", family="IBM Plex Mono"),
                showlegend=False,
                hovertemplate=f"League avg ({phase}): {_LEAGUE_AVG_SR[phase]:.0f}<extra></extra>",
            ))

    x_max = max(df_ph["strike_rate"].max() if not df_ph.empty else 200,
                max(_LEAGUE_AVG_SR.values(), default=0)) * 1.35

    fig_phase.update_layout(**CHART_THEME)
    fig_phase.update_layout(
        yaxis={"categoryorder": "array", "categoryarray": PHASE_ORDER[::-1]},
        margin={**CHART_THEME["margin"], "l": 80, "r": 40},
        xaxis={**CHART_THEME["xaxis"], "range": [0, x_max]},
    )

    phase_chart = [
        html.Span("Strike Rate by Phase  ·  tick = league avg", className="chart-card__label"),
        dcc.Graph(figure=fig_phase, config={"displayModeBar": False}, style={"height": "180px"}),
    ]

    # ── Matchup chart ─────────────────────────────────────────────────
    bm = (
        _matchups[_matchups["batter"] == player]
        .sort_values("dismissal_prob", ascending=False)
        .head(8)
    )

    if bm.empty:
        matchup_chart = [
            html.Span("Bowler Matchups", className="chart-card__label"),
            html.P("No matchup data - need 20+ balls vs a single bowler.",
                   style={"fontSize": "11px", "color": "#888", "marginTop": "12px"}),
        ]
    else:
        fig_match = go.Figure(go.Bar(
            x=bm["dismissal_prob"],
            y=bm["bowler"],
            orientation="h",
            marker_color="#3b82f6",
            marker_line_width=0,
            width=0.5,
            # dismissal_prob is stored as a percentage (e.g. 4.17 = 4.17%), not a decimal
            # using :.0% would multiply by 100 again - use :.1f% instead
            text=[f"{v:.1f}%" for v in bm["dismissal_prob"]],
            textposition="outside",
            textfont={"size": 10, "color": "#888"},
        ))
        fig_match.update_layout(**CHART_THEME)
        fig_match.update_layout(
            yaxis={"autorange": "reversed"},
            margin={**CHART_THEME["margin"], "l": 120, "r": 50},
            # axis shows raw percentage values (0-20), so append % without multiplying
            xaxis={**CHART_THEME["xaxis"], "ticksuffix": "%"},
        )
        matchup_chart = [
            html.Span("Dismissal Probability by Bowler", className="chart-card__label"),
            dcc.Graph(figure=fig_match, config={"displayModeBar": False}, style={"height": "180px"}),
        ]

    # ── Cluster badge (D) ─────────────────────────────────────────────
    # Only 36 batsmen qualified for clustering (20+ ball matchups vs multiple bowlers)
    profile_row = _profiles[_profiles["batter"] == player]
    if not profile_row.empty:
        cluster_id = int(profile_row.iloc[0]["cluster"])
        label, color = _CLUSTER_LABELS[cluster_id]
        cluster_badge = html.Span(
            label,
            className="cluster-badge",
            style={"backgroundColor": color + "22", "color": color, "borderColor": color + "55"},
        )
    else:
        cluster_badge = html.Span(
            "No cluster data",
            className="cluster-badge",
            style={"backgroundColor": "#f5f5f5", "color": "#bbb", "borderColor": "#e5e5e5"},
        )

    # ── Impact Score trend by season (C) ─────────────────────────────
    imp = _impact[_impact["player"] == player].sort_values("season")

    if imp.empty:
        impact_chart = [
            html.Span("Impact Score by Season", className="chart-card__label"),
            html.P("No impact data available.",
                   style={"fontSize": "11px", "color": "#888", "marginTop": "12px"}),
        ]
    else:
        # Color each bar by sign: positive (above avg) = blue, negative = red
        bar_colors = ["#3b82f6" if v >= 0 else "#ef4444" for v in imp["avg_impact"]]
        seasons    = [str(int(s)) for s in imp["season"]]

        fig_imp = go.Figure(go.Bar(
            x=seasons,
            y=imp["avg_impact"],
            marker_color=bar_colors,
            marker_line_width=0,
            text=[f"{v:+.2f}" for v in imp["avg_impact"]],
            textposition="outside",
            textfont={"size": 9, "color": "#888", "family": "IBM Plex Mono"},
            customdata=imp["matches_played"].values,
            hovertemplate="%{x}: <b>%{y:+.2f}</b><br>Matches: %{customdata}<extra></extra>",
        ))

        # Horizontal reference line at y=0 (league average)
        fig_imp.add_hline(y=0, line_dash="dot", line_color="#e5e5e5", line_width=1)

        # Extend y range so labels don't clip
        y_abs = imp["avg_impact"].abs().max()
        y_range = [-(y_abs * 1.5), y_abs * 1.5]

        fig_imp.update_layout(**CHART_THEME)
        fig_imp.update_layout(
            yaxis={**CHART_THEME["yaxis"], "range": y_range, "zeroline": False},
            xaxis={**CHART_THEME["xaxis"]},
        )

        impact_chart = [
            html.Span("Impact Score by Season  ·  0 = league average", className="chart-card__label"),
            dcc.Graph(figure=fig_imp, config={"displayModeBar": False}, style={"height": "180px"}),
        ]

    return metrics, phase_chart, matchup_chart, cluster_badge, impact_chart
