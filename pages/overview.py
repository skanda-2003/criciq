import dash
from dash import html, dcc, callback, Input, Output
import dash_bootstrap_components as dbc
import pandas as pd
import plotly.graph_objects as go

from components.metric_card import metric_card
from components.charts import phase_stacked_bar, CHART_THEME
from data.loader import DEL, MAT
from src.name_map import get_full_name

dash.register_page(__name__, path="/", name="Overview", title="CricIQ - Overview")

# ── Static data - venue chart uses pre-computed t-test results (2021-26 only) ──
# It can't respond to the season toggle without re-running scipy t-tests on the fly.
_ven = pd.read_csv("data/processed/venue_impact.csv")

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
_fig_venue.add_hline(y=_mean_rr, line_dash="dot", line_color="#ccc", line_width=1)
_fig_venue.update_layout(**CHART_THEME)
_fig_venue.update_layout(xaxis={"showline": False, "tickfont": {"family": "Inter, system-ui, sans-serif", "size": 9}})


def _finding(dot_color, children):
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

    html.Span(id="overview-title", className="section-label"),

    # Row 1 - metric cards (populated by callback)
    dbc.Row(id="overview-metrics", className="card-row"),

    # Row 2 - phase trend (dynamic) + venue chart (always 2021-26, pre-computed t-tests)
    dbc.Row([
        dbc.Col(
            html.Div([
                html.Span("Run Contribution by Phase · Per Season", className="chart-card__label"),
                dcc.Graph(id="overview-phase-chart", config={"displayModeBar": False}, style={"height": "220px"}),
            ], className="chart-card"),
            width=7,
        ),
        dbc.Col(
            html.Div([
                html.Span(
                    "Run Rate by Venue · Blue = above avg · Orange = below avg · 2021-26",
                    className="chart-card__label",
                ),
                dcc.Graph(figure=_fig_venue, config={"displayModeBar": False}, style={"height": "220px"}),
            ], className="chart-card"),
            width=5,
        ),
    ], className="card-row"),

    # Row 3 - death specialists (dynamic) + key findings (hardcoded 2021-26 analysis)
    dbc.Row([
        dbc.Col(
            html.Div([
                html.Span(id="overview-death-label", className="chart-card__label"),
                dcc.Graph(id="overview-death-chart", config={"displayModeBar": False}, style={"height": "260px"}),
            ], className="chart-card"),
            width=6,
        ),
        dbc.Col(
            html.Div([
                html.Span("Key Research Findings · 2021-26", className="chart-card__label"),
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


@callback(
    Output("overview-title",       "children"),
    Output("overview-metrics",     "children"),
    Output("overview-phase-chart", "figure"),
    Output("overview-death-chart", "figure"),
    Output("overview-death-label", "children"),
    Input("season-filter", "data"),
)
def update_overview(season_data):
    min_yr = season_data["min"]
    max_yr = season_data["max"]

    # Filter the shared DataFrames to the selected season window
    del_f = DEL[
        (DEL["season"] >= min_yr) &
        (DEL["season"] <= max_yr) &
        (~DEL["super_over"].astype(bool))
    ]
    mat_f = MAT[(MAT["season"] >= min_yr) & (MAT["season"] <= max_yr)]

    # Section title reflects which window is active
    title = "Season Overview · All Time (2008-2026)" if min_yr <= 2008 else f"Season Overview · {min_yr}-{max_yr}"

    # ── Metric cards ─────────────────────────────────────────────────
    n_matches = len(mat_f)

    avg_first = round(
        del_f[del_f["innings"] == 1]
        .groupby("match_id")["total_runs"].sum()
        .mean()
    )
    avg_powerplay = round(
        del_f[(del_f["innings"] == 1) & (del_f["phase"] == "powerplay")]
        .groupby("match_id")["total_runs"].sum()
        .mean()
    )
    avg_boundaries = round(
        del_f[del_f["is_boundary_4"] | del_f["is_boundary_6"]]
        .groupby("match_id")
        .size()
        .mean()
    )

    p_matches    = int(min(n_matches    / 500 * 100, 100))
    p_first      = int(min(avg_first    / 210 * 100, 100))
    p_powerplay  = int(min(avg_powerplay / 65 * 100, 100))
    p_boundaries = int(min(avg_boundaries / 50 * 100, 100))

    metrics = [
        dbc.Col(metric_card("Matches",            str(n_matches),      progress=p_matches,     color="blue"),   width=3),
        dbc.Col(metric_card("Avg 1st Innings",    str(avg_first),      secondary=" runs", progress=p_first,     color="blue"),   width=3),
        dbc.Col(metric_card("Avg Powerplay",      str(avg_powerplay),  secondary=" runs", progress=p_powerplay, color="green"),  width=3),
        dbc.Col(metric_card("Boundaries / Match", str(avg_boundaries), progress=p_boundaries,  color="orange"), width=3),
    ]

    # ── Phase stacked bar ─────────────────────────────────────────────
    phase_season = (
        del_f[del_f["innings"] == 1]
        .groupby(["season", "phase"])["total_runs"]
        .sum()
        .unstack(fill_value=0)
        .reset_index()
    )
    for _col in ["powerplay", "middle", "death"]:
        if _col not in phase_season.columns:
            phase_season[_col] = 0

    fig_phase = phase_stacked_bar(
        phase_season, x_col="season", pp_col="powerplay", mid_col="middle", death_col="death",
    )

    # ── Death specialists ─────────────────────────────────────────────
    # Computed from DEL directly so it responds to the season filter.
    # Wide deliveries are excluded: they don't count as balls faced by the batter.
    legal_death = del_f[
        (del_f["phase"] == "death") & (~del_f["is_wide"].astype(bool))
    ]

    death_stats = legal_death.groupby("batter").agg(
        balls_faced=("batter_runs", "count"),
        runs_scored=("batter_runs", "sum"),
    ).reset_index()
    death_stats["strike_rate"] = death_stats["runs_scored"] / death_stats["balls_faced"] * 100

    avg_pos = (
        legal_death.groupby("batter")["batting_position"]
        .mean()
        .reset_index()
        .rename(columns={"batting_position": "avg_position"})
    )
    death_stats = death_stats.merge(avg_pos, on="batter", how="left")

    specialists = (
        death_stats[(death_stats["balls_faced"] >= 50) & (death_stats["avg_position"] > 5)]
        .sort_values("strike_rate", ascending=False)
        .head(10)
        .reset_index(drop=True)
    )
    specialists["display_name"] = specialists["batter"].map(get_full_name)

    # League avg SR: weighted across all 50+ ball qualifiers (not just top 10)
    qualified = death_stats[death_stats["balls_faced"] >= 50]
    league_sr = qualified["runs_scored"].sum() / qualified["balls_faced"].sum() * 100

    fig_death = go.Figure(go.Bar(
        x=specialists["strike_rate"],
        y=specialists["display_name"],
        orientation="h",
        marker_color="#f97316",
        marker_line_width=0,
        width=0.5,
        text=[f"{v:.0f}  ({b} balls)" for v, b in
              zip(specialists["strike_rate"], specialists["balls_faced"])],
        textposition="outside",
        textfont={"size": 9, "color": "#aaa", "family": "IBM Plex Mono, monospace"},
        hovertemplate="<b>%{y}</b><br>Death SR: %{x:.0f}<extra></extra>",
    ))
    fig_death.add_vline(x=league_sr, line_dash="dot", line_color="#ccc", line_width=1)
    fig_death.update_layout(**CHART_THEME)
    fig_death.update_layout(
        yaxis={"autorange": "reversed", "tickfont": {"family": "Inter, system-ui, sans-serif", "size": 9}},
        margin={**CHART_THEME["margin"], "l": 130, "r": 90},
        xaxis={**CHART_THEME["xaxis"], "range": [0, 280]},
    )

    death_label = f"Death Specialists · SR in Overs 16-20 · Dashed = league avg {league_sr:.0f}"

    return title, metrics, fig_phase, fig_death, death_label
