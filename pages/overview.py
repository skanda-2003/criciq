import dash
from dash import html, dcc
import dash_bootstrap_components as dbc
import pandas as pd
import plotly.graph_objects as go

from components.metric_card import metric_card
from components.charts import phase_stacked_bar, CHART_THEME

dash.register_page(__name__, path="/", name="Overview", title="CricIQ - Overview")

# ── Load data once at server start ──────────────────────────────────
_del   = pd.read_csv("data/processed/deliveries.csv")
_mat   = pd.read_csv("data/processed/matches.csv")
_ven   = pd.read_csv("data/processed/venue_impact.csv")
_phase = pd.read_csv("data/processed/phase_batting.csv")

_del = _del[(_del["season"] >= 2021) & (~_del["super_over"].astype(bool))]
_mat = _mat[_mat["season"] >= 2021]

# ── Metric card values ───────────────────────────────────────────────
n_matches = len(_mat)

avg_first = round(
    _del[_del["innings"] == 1]
    .groupby("match_id")["total_runs"].sum()
    .mean()
)

avg_powerplay = round(
    _del[(_del["innings"] == 1) & (_del["phase"] == "powerplay")]
    .groupby("match_id")["total_runs"].sum()
    .mean()
)

avg_boundaries = round(
    _del[_del["is_boundary_4"] | _del["is_boundary_6"]]
    .groupby("match_id")
    .size()
    .mean()
)

_p_matches    = int(min(n_matches / 500 * 100, 100))
_p_first      = int(min(avg_first / 210 * 100, 100))
_p_powerplay  = int(min(avg_powerplay / 65 * 100, 100))
_p_boundaries = int(min(avg_boundaries / 50 * 100, 100))

# ── Phase stacked bar ────────────────────────────────────────────────
_phase_season = (
    _del[_del["innings"] == 1]
    .groupby(["season", "phase"])["total_runs"]
    .sum()
    .unstack(fill_value=0)
    .reset_index()
)
for _col in ["powerplay", "middle", "death"]:
    if _col not in _phase_season.columns:
        _phase_season[_col] = 0

_fig_phase = phase_stacked_bar(
    _phase_season, x_col="season", pp_col="powerplay", mid_col="middle", death_col="death",
)

# ── Venue intelligence chart (A) ─────────────────────────────────────
# Short names for the chart labels - the full names are shown in hover
_VENUE_SHORT = {
    "Arun Jaitley Stadium, Delhi":                                                           "Delhi",
    "M Chinnaswamy Stadium, Bengaluru":                                                      "Bengaluru",
    "Eden Gardens, Kolkata":                                                                 "Kolkata",
    "Rajiv Gandhi International Stadium, Uppal, Hyderabad":                                  "Hyderabad",
    "Sawai Mansingh Stadium, Jaipur":                                                        "Jaipur",
    "Narendra Modi Stadium, Ahmedabad":                                                      "Ahmedabad",
    "Wankhede Stadium, Mumbai":                                                              "Mumbai",
    "Bharat Ratna Shri Atal Bihari Vajpayee Ekana Cricket Stadium, Lucknow":                "Lucknow",
    "Maharaja Yadavindra Singh International Cricket Stadium, Mullanpur":                    "Mullanpur",
    "MA Chidambaram Stadium, Chepauk, Chennai":                                              "Chennai",
}

_ven_qual = (
    _ven[_ven["enough_data"]]
    .sort_values("run_rate", ascending=False)
    .reset_index(drop=True)
    .copy()
)
_ven_qual["short_name"] = _ven_qual["venue"].map(lambda v: _VENUE_SHORT.get(v, v[:18]))

# Color by significance and direction of Cohen's d:
# blue = significantly above average, orange = significantly below average, grey = not significant
def _venue_color(row):
    if pd.isna(row.get("significant")) or not row["significant"]:
        return "#d0d0d0"
    return "#3b82f6" if row["cohens_d"] > 0 else "#f97316"

_ven_qual["bar_color"] = _ven_qual.apply(_venue_color, axis=1)
_mean_rr = _ven_qual["run_rate"].mean()

_fig_venue = go.Figure(go.Bar(
    x=_ven_qual["short_name"],
    y=_ven_qual["run_rate"],
    marker_color=_ven_qual["bar_color"],
    marker_line_width=0,
    width=0.6,
    # Pass the full venue name, cohen's d, p-value, and match count into hover
    customdata=list(zip(
        _ven_qual["venue"],
        _ven_qual["cohens_d"].round(3).fillna(0),
        _ven_qual["p_value"].round(4).fillna(1),
        _ven_qual["matches"],
    )),
    hovertemplate=(
        "<b>%{customdata[0]}</b><br>"
        "Run Rate: <b>%{y:.2f}</b> per over<br>"
        "Cohen's d: %{customdata[1]}  ·  p = %{customdata[2]}<br>"
        "Matches: %{customdata[3]}<extra></extra>"
    ),
))
# Reference line at the mean run rate
_fig_venue.add_hline(y=_mean_rr, line_dash="dot", line_color="#ccc", line_width=1)
_fig_venue.update_layout(**CHART_THEME)
_fig_venue.update_layout(xaxis={"showline": False, "tickfont": {"family": "Inter, system-ui, sans-serif", "size": 9}})

# ── Death specialists leaderboard (B) ────────────────────────────────
# "Death specialist" = 50+ balls in death phase AND avg batting position > 5
# Batting position filter is critical: an opener surviving to the death is NOT a finisher

# Avg batting position per batter in death overs (from deliveries which has batting_position)
_avg_pos = (
    _del[_del["phase"] == "death"]
    .groupby("batter")["batting_position"]
    .mean()
    .reset_index()
    .rename(columns={"batting_position": "avg_position"})
)

_death = _phase[_phase["phase"] == "death"].merge(_avg_pos, on="batter", how="left")
_death_specialists = (
    _death[(_death["balls_faced"] >= 50) & (_death["avg_position"] > 5)]
    .sort_values("strike_rate", ascending=False)
    .head(10)
    .reset_index(drop=True)
)

# Expand abbreviated names for readability
_DEATH_NAMES = {
    "R Shepherd": "Romario Shepherd",
    "T Stubbs":   "Tristan Stubbs",
    "MP Stoinis": "Marcus Stoinis",
    "SB Dubey":   "Saurabh Dubey",
    "TH David":   "Tim David",
    "RK Singh":   "Rinku Singh",
}
_death_specialists["display_name"] = _death_specialists["batter"].map(
    lambda b: _DEATH_NAMES.get(b, b)
)

# League average death SR (50+ ball qualifiers) - used as a reference line
_LEAGUE_DEATH_SR = (
    _phase[(_phase["phase"] == "death") & (_phase["balls_faced"] >= 50)]["runs_scored"].sum()
    / _phase[(_phase["phase"] == "death") & (_phase["balls_faced"] >= 50)]["balls_faced"].sum()
    * 100
)

_fig_death = go.Figure(go.Bar(
    x=_death_specialists["strike_rate"],
    y=_death_specialists["display_name"],
    orientation="h",
    marker_color="#f97316",
    marker_line_width=0,
    width=0.5,
    text=[f"{v:.0f}  ({b} balls)" for v, b in
          zip(_death_specialists["strike_rate"], _death_specialists["balls_faced"])],
    textposition="outside",
    textfont={"size": 9, "color": "#aaa", "family": "IBM Plex Mono, monospace"},
    hovertemplate="<b>%{y}</b><br>Death SR: %{x:.0f}<extra></extra>",
))
# Reference line showing the league average death SR so context is immediate
_fig_death.add_vline(x=_LEAGUE_DEATH_SR, line_dash="dot", line_color="#ccc", line_width=1)
_fig_death.update_layout(**CHART_THEME)
_fig_death.update_layout(
    yaxis={"autorange": "reversed", "tickfont": {"family": "Inter, system-ui, sans-serif", "size": 9}},
    margin={**CHART_THEME["margin"], "l": 130, "r": 90},
    xaxis={**CHART_THEME["xaxis"], "range": [0, 280]},
)

# ── Helper - must be defined before layout references it ────────────
def _finding(dot_color, children):
    """Renders one finding row: a small colored dot + descriptive text."""
    return html.Div([
        html.Span(style={
            "width": "6px", "height": "6px", "borderRadius": "50%",
            "backgroundColor": dot_color, "display": "inline-block",
            "marginRight": "10px", "flexShrink": "0", "marginTop": "3px",
        }),
        html.Span(children, className="finding-text"),
    ], className="finding-row")


# ── Layout ───────────────────────────────────────────────────────────
layout = html.Div([

    html.Span("Season Overview · 2021–2026", className="section-label"),

    # Row 1 - metric cards
    dbc.Row([
        dbc.Col(metric_card("Matches",          str(n_matches),   progress=_p_matches,    color="blue"),   width=3),
        dbc.Col(metric_card("Avg 1st Innings",  str(avg_first),   secondary=" runs",
                            progress=_p_first,    color="blue"),   width=3),
        dbc.Col(metric_card("Avg Powerplay",    str(avg_powerplay), secondary=" runs",
                            progress=_p_powerplay, color="green"),  width=3),
        dbc.Col(metric_card("Boundaries / Match", str(avg_boundaries),
                            progress=_p_boundaries, color="orange"), width=3),
    ], className="card-row"),

    # Row 2 - phase trend + venue intelligence
    dbc.Row([
        dbc.Col(
            html.Div([
                html.Span("Run Contribution by Phase · Per Season", className="chart-card__label"),
                dcc.Graph(figure=_fig_phase, config={"displayModeBar": False}, style={"height": "220px"}),
            ], className="chart-card"),
            width=7,
        ),
        dbc.Col(
            html.Div([
                html.Span(
                    "Run Rate by Venue · Blue = significantly above avg · Orange = below avg · Dashed = league avg",
                    className="chart-card__label",
                ),
                dcc.Graph(figure=_fig_venue, config={"displayModeBar": False}, style={"height": "220px"}),
            ], className="chart-card"),
            width=5,
        ),
    ], className="card-row"),

    # Row 3 - death specialists + key research findings
    dbc.Row([
        dbc.Col(
            html.Div([
                html.Span(
                    f"Death Specialists · SR in Overs 16-20 · Dashed = league avg {_LEAGUE_DEATH_SR:.0f}",
                    className="chart-card__label",
                ),
                dcc.Graph(figure=_fig_death, config={"displayModeBar": False}, style={"height": "260px"}),
            ], className="chart-card"),
            width=6,
        ),
        dbc.Col(
            html.Div([
                html.Span("Key Research Findings", className="chart-card__label"),
                _finding("#f97316", [
                    html.Strong("Wankhede is not a batting paradise."),
                    " In 2021-26 it is statistically below average (p = 0.014, d = -0.02). "
                    "Delhi, Bengaluru, and Kolkata are the actual high-scoring grounds.",
                ]),
                _finding("#ef4444", [
                    html.Strong("Chennai is the hardest ground to bat on"),
                    " in this era - lowest run rate with the largest effect size (d = -0.10, p < 0.001). "
                    "Bowling-first at Chepauk is backed by data.",
                ]),
                _finding("#3b82f6", [
                    html.Strong("Death specialists are a distinct archetype."),
                    " Players who avg batting position > 5 in death overs - genuine finishers like "
                    "Rinku Singh, Tim David, and Shashank Singh - form a separate tier from openers who survive.",
                ]),
                _finding("#22c55e", [
                    html.Strong("run_rate_pressure was a top-3 feature"),
                    " in the win probability Random Forest model, validating the domain-motivated "
                    "engineering of required_rr / current_rr as a single ratio.",
                ]),
            ], className="chart-card findings-card"),
            width=6,
        ),
    ], className="card-row"),

])
