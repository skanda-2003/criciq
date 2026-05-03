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

# Players with at least 50 balls in any single phase
_players = sorted(_phase[_phase["balls_faced"] >= 50]["batter"].unique())

PHASE_ORDER  = ["powerplay", "middle", "death"]
PHASE_COLORS = {"powerplay": "#3b82f6", "middle": "#22c55e", "death": "#f97316"}

# ── Layout ───────────────────────────────────────────────────────────
layout = html.Div([

    html.Span("Player Deep-Dive · 2021–2026", className="section-label"),

    dbc.Row([
        dbc.Col(
            dcc.Dropdown(
                id="player-select",
                options=[{"label": p, "value": p} for p in _players],
                value=_players[0],
                clearable=False,
            ),
            width=4,
        ),
    ], className="card-row"),

    dbc.Row(id="player-metrics", className="card-row"),

    dbc.Row([
        dbc.Col(html.Div(id="player-phase-chart",   className="chart-card"), width=6),
        dbc.Col(html.Div(id="player-matchup-chart", className="chart-card"), width=6),
    ], className="card-row"),

])


@callback(
    Output("player-metrics",       "children"),
    Output("player-phase-chart",   "children"),
    Output("player-matchup-chart", "children"),
    Input("player-select", "value"),
)
def update_player(player):
    df = _phase[_phase["batter"] == player]

    # Aggregate across all phases for summary metrics
    total_balls      = df["balls_faced"].sum()
    total_runs       = df["runs_scored"].sum()
    total_boundaries = df["boundaries"].sum()
    total_dots       = df["dots"].sum()

    sr    = round(total_runs / total_balls * 100, 1) if total_balls > 0 else 0
    bpct  = round(total_boundaries / total_balls * 100, 1) if total_balls > 0 else 0
    dpct  = round(total_dots / total_balls * 100, 1) if total_balls > 0 else 0

    metrics = [
        dbc.Col(metric_card("Strike Rate",  str(sr),          progress=int(min(sr / 200 * 100, 100)),    color="blue"),   width=3),
        dbc.Col(metric_card("Balls Faced",  str(total_balls), progress=int(min(total_balls / 500 * 100, 100)), color="green"),  width=3),
        dbc.Col(metric_card("Boundary %",   f"{bpct}%",       progress=int(min(bpct / 40 * 100, 100)),   color="orange"), width=3),
        dbc.Col(metric_card("Dot Ball %",   f"{dpct}%",       progress=int(dpct),                         color="red"),    width=3),
    ]

    # Phase strike rate — horizontal bars, one per phase
    df_ph = df[df["phase"].isin(PHASE_ORDER)].set_index("phase").reindex(PHASE_ORDER).dropna()

    fig_phase = go.Figure(go.Bar(
        x=df_ph["strike_rate"],
        y=df_ph.index,
        orientation="h",
        marker_color=[PHASE_COLORS[p] for p in df_ph.index],
        marker_line_width=0,
        width=0.5,
        text=[f"{v:.0f}" for v in df_ph["strike_rate"]],
        textposition="outside",
        textfont={"size": 10, "color": "#888"},
    ))
    fig_phase.update_layout(**CHART_THEME)
    fig_phase.update_layout(
        yaxis={"categoryorder": "array", "categoryarray": PHASE_ORDER[::-1]},
        margin={**CHART_THEME["margin"], "l": 80, "r": 40},
        xaxis={**CHART_THEME["xaxis"], "range": [0, df_ph["strike_rate"].max() * 1.3 if not df_ph.empty else 200]},
    )

    phase_chart = [
        html.Span("Strike Rate by Phase", className="chart-card__label"),
        dcc.Graph(figure=fig_phase, config={"displayModeBar": False}, style={"height": "180px"}),
    ]

    # Matchup: bowlers this batter has faced most often, ranked by dismissal probability
    bm = (
        _matchups[_matchups["batter"] == player]
        .sort_values("dismissal_prob", ascending=False)
        .head(8)
    )

    if bm.empty:
        matchup_chart = [
            html.Span("Bowler Matchups", className="chart-card__label"),
            html.P("No matchup data — need 20+ balls vs a single bowler.",
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
            text=[f"{v:.0%}" for v in bm["dismissal_prob"]],
            textposition="outside",
            textfont={"size": 10, "color": "#888"},
        ))
        fig_match.update_layout(**CHART_THEME)
        fig_match.update_layout(
            yaxis={"autorange": "reversed"},
            margin={**CHART_THEME["margin"], "l": 120, "r": 50},
            xaxis={**CHART_THEME["xaxis"], "tickformat": ".0%"},
        )
        matchup_chart = [
            html.Span("Dismissal Probability by Bowler", className="chart-card__label"),
            dcc.Graph(figure=fig_match, config={"displayModeBar": False}, style={"height": "180px"}),
        ]

    return metrics, phase_chart, matchup_chart
