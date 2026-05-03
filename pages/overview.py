import dash
from dash import html, dcc
import dash_bootstrap_components as dbc
import pandas as pd

from components.metric_card import metric_card
from components.charts import phase_stacked_bar, venue_bar, empty_figure

dash.register_page(__name__, path="/", name="Overview", title="CricIQ - Overview")

# ── Load data once at server start ──────────────────────────────────
# Paths are relative to project root — run the app from there with: python app.py
_del = pd.read_csv("data/processed/deliveries.csv")
_mat = pd.read_csv("data/processed/matches.csv")
_ven = pd.read_csv("data/processed/venue_impact.csv")

# Default 2021+ filter applied here; all stats below reflect this window
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

# Progress bar values: each metric scaled to a meaningful reference ceiling
_p_matches    = int(min(n_matches / 500 * 100, 100))    # 500 = approx max for this window
_p_first      = int(min(avg_first / 210 * 100, 100))    # 210 = high reference score
_p_powerplay  = int(min(avg_powerplay / 65 * 100, 100)) # 65 = high powerplay reference
_p_boundaries = int(min(avg_boundaries / 50 * 100, 100)) # 50 = high boundary reference

# ── Phase stacked bar: total runs by phase across seasons ────────────
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

# ── Venue bar: qualified venues only, sorted by run rate ────────────
_ven_chart = (
    _ven[_ven["enough_data"]]
    .sort_values("run_rate", ascending=False)
    .reset_index(drop=True)
)

# ── Build Plotly figures ─────────────────────────────────────────────
_fig_phase = phase_stacked_bar(
    _phase_season,
    x_col="season",
    pp_col="powerplay",
    mid_col="middle",
    death_col="death",
)

_fig_venue = venue_bar(_ven_chart, venue_col="venue", metric_col="run_rate")
_fig_venue.update_layout(xaxis={"tickangle": -35})  # rotate long venue names

# ── Layout ───────────────────────────────────────────────────────────
layout = html.Div([

    html.Span("Season Overview · 2021–2026", className="section-label"),

    # Row 1 — metric cards
    dbc.Row([
        dbc.Col(metric_card(
            "Matches",
            str(n_matches),
            progress=_p_matches,
            color="blue",
        ), width=3),
        dbc.Col(metric_card(
            "Avg 1st Innings",
            str(avg_first),
            secondary=" runs",
            progress=_p_first,
            color="blue",
        ), width=3),
        dbc.Col(metric_card(
            "Avg Powerplay",
            str(avg_powerplay),
            secondary=" runs",
            progress=_p_powerplay,
            color="green",
        ), width=3),
        dbc.Col(metric_card(
            "Boundaries / Match",
            str(avg_boundaries),
            progress=_p_boundaries,
            color="orange",
        ), width=3),
    ], className="card-row"),

    # Row 2 — charts
    dbc.Row([
        dbc.Col(
            html.Div([
                html.Span("Run Contribution by Phase · Per Season", className="chart-card__label"),
                dcc.Graph(
                    figure=_fig_phase,
                    config={"displayModeBar": False},
                    style={"height": "260px"},
                ),
            ], className="chart-card"),
            width=7,
        ),
        dbc.Col(
            html.Div([
                html.Span("Run Rate by Venue · Runs per Over", className="chart-card__label"),
                dcc.Graph(
                    figure=_fig_venue,
                    config={"displayModeBar": False},
                    style={"height": "260px"},
                ),
            ], className="chart-card"),
            width=5,
        ),
    ], className="card-row"),

])
