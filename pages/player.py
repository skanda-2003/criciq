import dash
from dash import html, dcc, callback, Input, Output
import dash_bootstrap_components as dbc
import pandas as pd
import plotly.graph_objects as go

from components.metric_card import metric_card
from components.charts import CHART_THEME
from src.name_map import get_full_name as _display_name
from data.loader import DEL

dash.register_page(__name__, path="/player", name="Player Deep-Dive", title="CricIQ - Player")

# ── Per-player pre-computed data (matchups + cluster stay 2021-26) ───
_matchups = pd.read_csv("data/processed/bowler_matchups.csv")
_profiles = pd.read_csv("data/processed/batsman_profiles.csv")
_impact   = pd.read_csv("data/processed/player_impact_season.csv")

PHASE_ORDER  = ["powerplay", "middle", "death"]
PHASE_COLORS = {"powerplay": "#3b82f6", "middle": "#22c55e", "death": "#f97316"}

# ── Pre-compute league averages for both season windows ──────────────
# Runs once at startup. The callback picks the right dict based on the store.
# League avg SR is weighted: total batter_runs / total legal balls, for players
# with 50+ balls in that phase (same threshold as the player leaderboards).
def _compute_league_avgs(del_legal):
    avgs = {}
    for ph in PHASE_ORDER:
        ph_del     = del_legal[del_legal["phase"] == ph]
        per_player = ph_del.groupby("batter").size()
        qualified  = per_player[per_player >= 50].index
        q          = ph_del[ph_del["batter"].isin(qualified)]
        if len(q) > 0:
            avgs[ph] = q["batter_runs"].sum() / len(q) * 100
    return avgs


_DEL_RECENT_LEGAL  = DEL[
    (DEL["season"] >= 2021) & (~DEL["super_over"].astype(bool)) & (~DEL["is_wide"].astype(bool))
]
_DEL_ALLTIME_LEGAL = DEL[
    (~DEL["super_over"].astype(bool)) & (~DEL["is_wide"].astype(bool))
]

_LEAGUE_AVG_SR_RECENT  = _compute_league_avgs(_DEL_RECENT_LEGAL)
_LEAGUE_AVG_SR_ALLTIME = _compute_league_avgs(_DEL_ALLTIME_LEGAL)

# Player dropdown stays 2021-26 era players (those we know are relevant).
# Switching to "All time" shows their career stats, it doesn't change who's in the list.
_phase_counts = _DEL_RECENT_LEGAL.groupby(["batter", "phase"]).size().reset_index(name="balls")
_players      = sorted(_phase_counts[_phase_counts["balls"] >= 50]["batter"].unique())

# Cluster archetype labels from k-means output in notebook 03
_CLUSTER_LABELS = {
    0: ("Consistent Striker", "#22c55e"),
    1: ("Aggressive Hitter",  "#f97316"),
    2: ("Steady Builder",     "#888888"),
    3: ("Power Hitter",       "#3b82f6"),
}

# ── Layout ───────────────────────────────────────────────────────────
layout = html.Div([

    html.Span(id="player-title", className="section-label"),

    # Row 1: player dropdown + cluster badge
    dbc.Row([
        dbc.Col(
            dcc.Dropdown(
                id="player-select",
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

    # Row 3: phase SR chart + matchup chart
    dbc.Row([
        dbc.Col(html.Div(id="player-phase-chart",   className="chart-card"), width=6),
        dbc.Col(html.Div(id="player-matchup-chart", className="chart-card"), width=6),
    ], className="card-row"),

    # Row 4: impact score trend
    dbc.Row([
        dbc.Col(html.Div(id="player-impact-chart", className="chart-card"), width=6),
    ], className="card-row"),

])


@callback(
    Output("player-title",         "children"),
    Output("player-metrics",       "children"),
    Output("player-phase-chart",   "children"),
    Output("player-matchup-chart", "children"),
    Output("player-cluster-badge", "children"),
    Output("player-impact-chart",  "children"),
    Input("player-select",  "value"),
    Input("season-filter",  "data"),
)
def update_player(player, season_data):
    min_yr = season_data["min"]
    max_yr = season_data["max"]

    # Legal balls for this player in the selected window (wides excluded throughout)
    player_legal = DEL[
        (DEL["batter"]     == player) &
        (DEL["season"]     >= min_yr) &
        (DEL["season"]     <= max_yr) &
        (~DEL["super_over"].astype(bool)) &
        (~DEL["is_wide"]   .astype(bool))
    ]

    # League averages for the selected window
    league_avgs = _LEAGUE_AVG_SR_RECENT if min_yr >= 2021 else _LEAGUE_AVG_SR_ALLTIME

    title = "Player Deep-Dive · All Time (2008-2026)" if min_yr <= 2008 else f"Player Deep-Dive · {min_yr}-{max_yr}"

    # ── Metric cards ─────────────────────────────────────────────────
    total_balls      = len(player_legal)
    total_runs       = int(player_legal["batter_runs"].sum())
    total_boundaries = int(
        (player_legal["is_boundary_4"].astype(bool) | player_legal["is_boundary_6"].astype(bool)).sum()
    )
    total_dots = int(player_legal["is_dot"].astype(bool).sum())

    sr   = round(total_runs / total_balls * 100, 1) if total_balls > 0 else 0
    bpct = round(total_boundaries / total_balls * 100, 1) if total_balls > 0 else 0
    dpct = round(total_dots       / total_balls * 100, 1) if total_balls > 0 else 0

    metrics = [
        dbc.Col(metric_card("Strike Rate", str(sr),          progress=int(min(sr / 200 * 100, 100)),          color="blue"),   width=3),
        dbc.Col(metric_card("Balls Faced", str(total_balls), progress=int(min(total_balls / 500 * 100, 100)), color="green"),  width=3),
        dbc.Col(metric_card("Boundary %",  f"{bpct}%",       progress=int(min(bpct / 40 * 100, 100)),          color="orange"), width=3),
        dbc.Col(metric_card("Dot Ball %",  f"{dpct}%",       progress=int(dpct),                               color="red"),    width=3),
    ]

    # ── Phase SR chart ────────────────────────────────────────────────
    # Computed from DEL directly so this responds to the season filter.
    phase_rows = []
    for ph in PHASE_ORDER:
        ph_del = player_legal[player_legal["phase"] == ph]
        balls  = len(ph_del)
        if balls > 0:
            phase_rows.append({
                "phase":       ph,
                "strike_rate": ph_del["batter_runs"].sum() / balls * 100,
                "balls_faced": balls,
            })

    df_ph = (
        pd.DataFrame(phase_rows).set_index("phase").reindex(PHASE_ORDER).dropna()
        if phase_rows else pd.DataFrame()
    )

    fig_phase = go.Figure()

    if not df_ph.empty:
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

        for phase in df_ph.index:
            if phase in league_avgs:
                fig_phase.add_trace(go.Scatter(
                    x=[league_avgs[phase]],
                    y=[phase],
                    mode="markers+text",
                    marker=dict(symbol="line-ns-open", size=22, color="#ccc",
                                line=dict(width=2, color="#ccc")),
                    text=[f"avg {league_avgs[phase]:.0f}"],
                    textposition="bottom center",
                    textfont=dict(size=9, color="#aaa", family="IBM Plex Mono"),
                    showlegend=False,
                    hovertemplate=f"League avg ({phase}): {league_avgs[phase]:.0f}<extra></extra>",
                ))

    x_max = max(
        df_ph["strike_rate"].max() if not df_ph.empty else 200,
        max(league_avgs.values(), default=0),
    ) * 1.35

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

    # ── Matchup chart - pre-computed 2021-26, does not change with filter ──
    bm = (
        _matchups[_matchups["batter"] == player]
        .sort_values("dismissal_prob", ascending=False)
        .head(8)
    )

    if bm.empty:
        matchup_chart = [
            html.Span("Bowler Matchups · 2021-26", className="chart-card__label"),
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
            text=[f"{v:.1f}%" for v in bm["dismissal_prob"]],
            textposition="outside",
            textfont={"size": 10, "color": "#888"},
        ))
        fig_match.update_layout(**CHART_THEME)
        fig_match.update_layout(
            yaxis={"autorange": "reversed"},
            margin={**CHART_THEME["margin"], "l": 120, "r": 50},
            xaxis={**CHART_THEME["xaxis"], "ticksuffix": "%"},
        )
        matchup_chart = [
            html.Span("Dismissal Probability by Bowler · 2021-26", className="chart-card__label"),
            dcc.Graph(figure=fig_match, config={"displayModeBar": False}, style={"height": "180px"}),
        ]

    # ── Cluster badge - pre-computed 2021-26, does not change with filter ──
    profile_row = _profiles[_profiles["batter"] == player]
    if not profile_row.empty:
        cluster_id    = int(profile_row.iloc[0]["cluster"])
        label, color  = _CLUSTER_LABELS[cluster_id]
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

    # ── Impact score trend ────────────────────────────────────────────
    imp = _impact[
        (_impact["player"] == player) &
        (_impact["season"] >= min_yr) &
        (_impact["season"] <= max_yr)
    ].sort_values("season")

    if imp.empty:
        impact_chart = [
            html.Span("Impact Score by Season", className="chart-card__label"),
            html.P("No impact data available.",
                   style={"fontSize": "11px", "color": "#888", "marginTop": "12px"}),
        ]
    else:
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

        fig_imp.add_hline(y=0, line_dash="dot", line_color="#e5e5e5", line_width=1)

        y_abs   = imp["avg_impact"].abs().max()
        y_range = [-(y_abs * 1.5), y_abs * 1.5]

        fig_imp.update_layout(**CHART_THEME)
        fig_imp.update_layout(
            yaxis={**CHART_THEME["yaxis"], "range": y_range, "zeroline": False},
            xaxis={**CHART_THEME["xaxis"]},
        )

        impact_chart = [
            html.Span("Impact Score by Season · 2021-26  ·  0 = league average", className="chart-card__label"),
            dcc.Graph(figure=fig_imp, config={"displayModeBar": False}, style={"height": "180px"}),
        ]

    return title, metrics, phase_chart, matchup_chart, cluster_badge, impact_chart
