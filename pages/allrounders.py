import dash
from dash import html, dcc, callback, Input, Output
import dash_bootstrap_components as dbc
import pandas as pd
import plotly.graph_objects as go

from components.metric_card import metric_card
from components.charts import CHART_THEME
from data.loader import DEL
from src.name_map import get_full_name

dash.register_page(__name__, path="/allrounders", name="Allrounders", title="CricIQ - Allrounders")

# Pre-computed z-scores; season column lets the callback filter by window
_IMPACT = pd.read_csv("data/processed/player_impact_season.csv")

# Canonical short team names for the depth chart
_TEAM_SHORT = {
    "Mumbai Indians":              "MI",
    "Lucknow Super Giants":        "LSG",
    "Delhi Capitals":              "DC",
    "Delhi Daredevils":            "DC",
    "Kolkata Knight Riders":       "KKR",
    "Sunrisers Hyderabad":         "SRH",
    "Rajasthan Royals":            "RR",
    "Punjab Kings":                "PBKS",
    "Kings XI Punjab":             "PBKS",
    "Royal Challengers Bengaluru": "RCB",
    "Royal Challengers Bangalore": "RCB",
    "Chennai Super Kings":         "CSK",
    "Gujarat Titans":              "GT",
    "Rising Pune Supergiant":      "RPS",
    "Rising Pune Supergiants":     "RPS",
}


def _finding(dot_color, children):
    return html.Div([
        html.Span(style={
            "width": "6px", "height": "6px", "borderRadius": "50%",
            "backgroundColor": dot_color, "display": "inline-block",
            "marginRight": "10px", "flexShrink": "0", "marginTop": "3px",
        }),
        html.Span(children, className="finding-text"),
    ], className="finding-row")


layout = html.Div([

    html.Span(id="ar-title", className="section-label"),

    # Row 1 - dual contribution scatter (flagship - full width)
    dbc.Row([
        dbc.Col(
            html.Div([
                html.Span(id="ar-scatter-label", className="chart-card__label"),
                dcc.Graph(id="ar-scatter-chart", config={"displayModeBar": False}, style={"height": "440px"}),
            ], className="chart-card"),
            width=12,
        ),
    ], className="card-row"),

    # Row 2 - metric cards
    dbc.Row(id="ar-metrics", className="card-row"),

    # Row 3 - combined impact leaderboard + per-team depth
    dbc.Row([
        dbc.Col(
            html.Div([
                html.Span(id="ar-leaderboard-label", className="chart-card__label"),
                dcc.Graph(id="ar-leaderboard-chart", config={"displayModeBar": False}, style={"height": "360px"}),
            ], className="chart-card"),
            width=5,
        ),
        dbc.Col(
            html.Div([
                html.Span(id="ar-depth-label", className="chart-card__label"),
                dcc.Graph(id="ar-depth-chart", config={"displayModeBar": False}, style={"height": "360px"}),
            ], className="chart-card"),
            width=7,
        ),
    ], className="card-row"),

    # Row 4 - season-best allrounder + key findings
    dbc.Row([
        dbc.Col(
            html.Div([
                html.Span(id="ar-season-label", className="chart-card__label"),
                dcc.Graph(id="ar-season-chart", config={"displayModeBar": False}, style={"height": "220px"}),
            ], className="chart-card"),
            width=8,
        ),
        dbc.Col(
            html.Div([
                html.Span("Key Findings · 2021-26", className="chart-card__label"),
                _finding("#3b82f6", [
                    html.Strong("Only 5 of 119 qualified allrounders sit in the elite quadrant"),
                    " (positive z-score in both departments, 50+ balls in both). Genuine "
                    "two-department contributors are the rarest archetype in IPL cricket.",
                ]),
                _finding("#22c55e", [
                    html.Strong("Sunil Narine leads the combined leaderboard (1.07)."),
                    " His 0.82 bowling z + 0.25 batting z over 5 seasons is the only "
                    "sustained two-department contribution in this era.",
                ]),
                _finding("#f97316", [
                    html.Strong("Jasprit Bumrah places 3rd in combined z-score (0.68)"),
                    " despite near-zero batting. This shows how dominant bowling alone "
                    "can elevate a combined score - it is not the same as being balanced.",
                ]),
                _finding("#ef4444", [
                    html.Strong("Abhishek Sharma won the season crown two years running (2025-26)."),
                    " A left-handed opening bat who also bowls left-arm spin, "
                    "he is one of very few players sustaining elite allrounder status "
                    "across consecutive seasons.",
                ]),
            ], className="chart-card findings-card"),
            width=4,
        ),
    ], className="card-row"),

])


@callback(
    Output("ar-title",            "children"),
    Output("ar-scatter-chart",    "figure"),
    Output("ar-scatter-label",    "children"),
    Output("ar-metrics",          "children"),
    Output("ar-leaderboard-chart","figure"),
    Output("ar-leaderboard-label","children"),
    Output("ar-depth-chart",      "figure"),
    Output("ar-depth-label",      "children"),
    Output("ar-season-chart",     "figure"),
    Output("ar-season-label",     "children"),
    Input("season-filter", "data"),
)
def update_allrounders(season_data):
    min_yr = season_data["min"]
    max_yr = season_data["max"]

    title = (
        "Allrounders · All Time (2008-2026)"
        if min_yr <= 2008
        else f"Allrounders · {min_yr}-{max_yr}"
    )

    # Filter the pre-computed impact CSV to the selected window.
    # The CSV only has 2021-26 data, so "all time" still shows 2021-26.
    # Require 50+ legal balls bowled to qualify as a bowler - this removes
    # occasional bowlers like TM Head (10 balls) who inflate the allrounder count.
    del_window = DEL[
        (DEL["season"] >= min_yr) & (DEL["season"] <= max_yr) &
        (~DEL["super_over"]) & (~DEL["is_wide"])
    ]
    bowl_qualified = set(
        del_window.groupby("bowler").size()
        .loc[lambda s: s >= 50]
        .index
    )
    # Batting qualification: 50+ balls faced total in the window.
    # Without this, pure bowlers with a batting z-score (even from minimal batting)
    # would appear - Bumrah, Chakravarthy, Markande etc. are not allrounders.
    bat_qualified = set(
        del_window[~del_window["is_wide"]]
        .groupby("batter").size()
        .loc[lambda s: s >= 50]
        .index
    )

    impact_f = _IMPACT[
        (_IMPACT["season"] >= min_yr) &
        (_IMPACT["season"] <= max_yr) &
        (_IMPACT["avg_bowling_z"].notna()) &
        (_IMPACT["avg_batting_z"].notna()) &
        (_IMPACT["player"].isin(bowl_qualified)) &
        (_IMPACT["player"].isin(bat_qualified))
    ].copy()

    # ── Career averages: mean z-scores across all seasons in the window ──
    career = impact_f.groupby("player").agg(
        avg_bat_z =("avg_batting_z", "mean"),
        avg_bowl_z=("avg_bowling_z", "mean"),
        seasons   =("season", "nunique"),
        matches   =("matches_played", "sum"),
    ).reset_index()
    career["combined_z"]   = career["avg_bat_z"] + career["avg_bowl_z"]
    career["display_name"] = career["player"].map(get_full_name)

    # ── Chart A: Dual contribution scatter ───────────────────────────
    # Label only the "Elite Allrounder" quadrant (both z > 0); hover for everyone
    elite_mask  = (career["avg_bat_z"] > 0) & (career["avg_bowl_z"] > 0)
    non_elite   = career[~elite_mask].reset_index(drop=True)
    elite       = career[elite_mask].reset_index(drop=True)

    # Axis ranges: pad the data extent slightly
    bat_abs  = max(abs(career["avg_bat_z"].min()),  abs(career["avg_bat_z"].max()))  + 0.2
    bowl_abs = max(abs(career["avg_bowl_z"].min()), abs(career["avg_bowl_z"].max())) + 0.2

    fig_scatter = go.Figure()

    # Shaded quadrant backgrounds drawn below the data points
    # Elite: light green  |  Bowling-heavy: light orange
    # Batting-heavy: light blue  |  Below avg: light grey
    for x0, x1, y0, y1, color in [
        (-5,  0,  0,  5, "rgba(249,115, 22,0.06)"),  # bowling-heavy (top-left)
        ( 0,  5,  0,  5, "rgba( 34,197, 94,0.06)"),  # elite (top-right)
        ( 0,  5, -5,  0, "rgba( 59,130,246,0.06)"),  # batting-heavy (bottom-right)
        (-5,  0, -5,  0, "rgba(200,200,200,0.08)"),  # below avg (bottom-left)
    ]:
        fig_scatter.add_shape(
            type="rect", x0=x0, x1=x1, y0=y0, y1=y1,
            xref="x", yref="y",
            fillcolor=color, layer="below", line_width=0,
        )

    # Grey dots for everyone outside the elite quadrant
    if not non_elite.empty:
        fig_scatter.add_trace(go.Scatter(
            x=non_elite["avg_bat_z"],
            y=non_elite["avg_bowl_z"],
            mode="markers",
            marker={"size": 6, "color": "#d0d0d0", "line": {"width": 0}},
            customdata=non_elite[["display_name", "avg_bat_z", "avg_bowl_z", "seasons", "matches"]].values,
            hovertemplate=(
                "<b>%{customdata[0]}</b><br>"
                "Batting z: <b>%{customdata[1]:.3f}</b><br>"
                "Bowling z: <b>%{customdata[2]:.3f}</b><br>"
                "%{customdata[3]:.0f} seasons · %{customdata[4]:.0f} matches"
                "<extra></extra>"
            ),
            showlegend=False,
        ))

    # Blue dots + name labels for elite allrounders only
    if not elite.empty:
        fig_scatter.add_trace(go.Scatter(
            x=elite["avg_bat_z"],
            y=elite["avg_bowl_z"],
            mode="markers+text",
            text=elite["display_name"],
            textposition="top center",
            textfont={"size": 8, "color": "#111", "family": "IBM Plex Mono, monospace"},
            marker={"size": 7, "color": "#22c55e", "line": {"width": 0}},
            customdata=elite[["display_name", "avg_bat_z", "avg_bowl_z", "seasons", "matches"]].values,
            hovertemplate=(
                "<b>%{customdata[0]}</b><br>"
                "Batting z: <b>%{customdata[1]:.3f}</b><br>"
                "Bowling z: <b>%{customdata[2]:.3f}</b><br>"
                "%{customdata[3]:.0f} seasons · %{customdata[4]:.0f} matches"
                "<extra></extra>"
            ),
            showlegend=False,
        ))

    # Reference lines at z=0 for both axes
    fig_scatter.add_vline(x=0, line_color="#e0e0e0", line_width=1)
    fig_scatter.add_hline(y=0, line_color="#e0e0e0", line_width=1)

    fig_scatter.update_layout(**CHART_THEME)
    fig_scatter.update_layout(
        xaxis={
            "range": [-bat_abs,  bat_abs],
            "title": {"text": "Batting Impact (z-score)", "font": {"family": "Inter, system-ui, sans-serif", "size": 9, "color": "#888"}},
        },
        yaxis={
            "range": [-bowl_abs, bowl_abs],
            "title": {"text": "Bowling Impact (z-score)", "font": {"family": "Inter, system-ui, sans-serif", "size": 9, "color": "#888"}},
        },
        annotations=[
            dict(x=0.98, y=0.98, xref="paper", yref="paper",
                 text="Elite Allrounder", showarrow=False,
                 xanchor="right", yanchor="top",
                 font={"size": 9, "color": "#22c55e", "family": "Inter, system-ui, sans-serif"}),
            dict(x=0.02, y=0.98, xref="paper", yref="paper",
                 text="Bowling-heavy", showarrow=False,
                 xanchor="left", yanchor="top",
                 font={"size": 9, "color": "#f97316", "family": "Inter, system-ui, sans-serif"}),
            dict(x=0.98, y=0.02, xref="paper", yref="paper",
                 text="Batting-heavy", showarrow=False,
                 xanchor="right", yanchor="bottom",
                 font={"size": 9, "color": "#3b82f6", "family": "Inter, system-ui, sans-serif"}),
            dict(x=0.02, y=0.02, xref="paper", yref="paper",
                 text="Below avg", showarrow=False,
                 xanchor="left", yanchor="bottom",
                 font={"size": 9, "color": "#888", "family": "Inter, system-ui, sans-serif"}),
        ],
        margin={**CHART_THEME["margin"], "l": 50, "r": 20, "b": 40},
    )

    n_elite       = int(elite_mask.sum())
    n_allrounders = len(career)
    scatter_label = (
        f"Dual Contribution · Batting z vs Bowling z · Career avg across seasons in window "
        f"· {n_elite} elite allrounders (both > 0) of {n_allrounders} qualified"
    )

    # ── Metric cards ─────────────────────────────────────────────────
    best_combined_row = career.loc[career["combined_z"].idxmax()]
    best_bat_row      = career.loc[career["avg_bat_z"].idxmax()]
    best_bowl_row     = career.loc[career["avg_bowl_z"].idxmax()]

    # Progress bars: combined z is typically < 2.5 at elite level; individual z < 1.5
    p_n     = int(min(n_allrounders / 150 * 100, 100))
    p_comb  = int(min(max(best_combined_row["combined_z"], 0) / 2.5 * 100, 100))
    p_bat   = int(min(max(best_bat_row["avg_bat_z"],  0) / 2.0 * 100, 100))
    p_bowl  = int(min(max(best_bowl_row["avg_bowl_z"], 0) / 1.5 * 100, 100))

    metrics = [
        dbc.Col(metric_card(
            "Allrounder Qualifiers",
            str(n_allrounders),
            secondary=" players",
            progress=p_n, color="blue",
        ), width=3),
        dbc.Col(metric_card(
            "Highest Combined Impact",
            f"{best_combined_row['combined_z']:.2f}",
            secondary=f" · {get_full_name(best_combined_row['player'])}",
            progress=p_comb, color="green",
        ), width=3),
        dbc.Col(metric_card(
            "Best Batting Allrounder",
            f"{best_bat_row['avg_bat_z']:.2f}",
            secondary=f" · {get_full_name(best_bat_row['player'])}",
            progress=p_bat, color="blue",
        ), width=3),
        dbc.Col(metric_card(
            "Best Bowling Allrounder",
            f"{best_bowl_row['avg_bowl_z']:.2f}",
            secondary=f" · {get_full_name(best_bowl_row['player'])}",
            progress=p_bowl, color="orange",
        ), width=3),
    ]

    # ── Chart B: Combined impact leaderboard ─────────────────────────
    top15 = career.sort_values("combined_z", ascending=False).head(15).reset_index(drop=True)

    fig_lb = go.Figure(go.Bar(
        x=top15["combined_z"],
        y=top15["display_name"],
        orientation="h",
        marker_color="#22c55e",
        marker_line_width=0,
        width=0.5,
        text=[f"{v:.2f}" for v in top15["combined_z"]],
        textposition="outside",
        textfont={"size": 9, "color": "#777", "family": "IBM Plex Mono, monospace"},
        hovertemplate="<b>%{y}</b><br>Combined z: %{x:.2f}<extra></extra>",
    ))
    fig_lb.update_layout(**CHART_THEME)
    fig_lb.update_layout(
        yaxis={
            "autorange": "reversed",
            "tickmode": "array",
            "tickvals": top15["display_name"].tolist(),
            "ticktext": top15["display_name"].tolist(),
            "tickfont": {"family": "Inter, system-ui, sans-serif", "size": 9},
        },
        margin={**CHART_THEME["margin"], "l": 130, "r": 60},
        xaxis={**CHART_THEME["xaxis"], "range": [0, top15["combined_z"].max() * 1.35]},
    )
    lb_label = f"Combined Impact Leaderboard · Batting z + Bowling z · {min_yr}-{max_yr}"

    # ── Chart C: Per-team allrounder depth ───────────────────────────
    # Find each allrounder's primary team from DEL (most matches as batter for that team)
    allrounder_names = career["player"].tolist()
    del_f = DEL[
        (DEL["season"] >= min_yr) &
        (DEL["season"] <= max_yr) &
        (~DEL["super_over"]) &
        (~DEL["is_wide"])
    ]
    team_counts = (
        del_f[del_f["batter"].isin(allrounder_names)]
        .groupby(["batter", "batting_team"])["match_id"]
        .nunique()
        .reset_index(name="matches")
    )
    primary_team = (
        team_counts.sort_values("matches", ascending=False)
        .drop_duplicates("batter")[["batter", "batting_team"]]
    )
    primary_team["batting_team"] = primary_team["batting_team"].map(
        lambda t: _TEAM_SHORT.get(t, t[:4])
    )
    depth = (
        primary_team["batting_team"]
        .value_counts()
        .reset_index()
    )
    depth.columns = ["team", "count"]
    depth = depth.sort_values("count", ascending=False).reset_index(drop=True)

    fig_depth = go.Figure(go.Bar(
        x=depth["count"],
        y=depth["team"],
        orientation="h",
        marker_color="#3b82f6",
        marker_line_width=0,
        width=0.5,
        text=depth["count"].astype(str),
        textposition="outside",
        textfont={"size": 9, "color": "#777", "family": "IBM Plex Mono, monospace"},
        hovertemplate="<b>%{y}</b><br>Allrounders: %{x}<extra></extra>",
    ))
    fig_depth.update_layout(**CHART_THEME)
    fig_depth.update_layout(
        yaxis={
            "autorange": "reversed",
            "tickmode": "array",
            "tickvals": depth["team"].tolist(),
            "ticktext": depth["team"].tolist(),
            "tickfont": {"family": "Inter, system-ui, sans-serif", "size": 9},
        },
        margin={**CHART_THEME["margin"], "l": 55, "r": 40},
        xaxis={**CHART_THEME["xaxis"], "range": [0, depth["count"].max() * 1.3]},
    )
    depth_label = f"Allrounder Depth by Franchise · Primary team by matches · {min_yr}-{max_yr}"

    # ── Chart D: Season-best allrounder ──────────────────────────────
    impact_f["combined_z"] = impact_f["avg_batting_z"] + impact_f["avg_bowling_z"]
    season_best = (
        impact_f.loc[impact_f.groupby("season")["combined_z"].idxmax()]
        .copy()
        .sort_values("season")
        .reset_index(drop=True)
    )
    season_best["display_name"] = season_best["player"].map(get_full_name)
    # Short label: last name only for bars (keeps chart readable)
    season_best["short_name"] = season_best["display_name"].apply(
        lambda n: n.split()[-1] if " " in n else n
    )
    season_best["season_str"] = season_best["season"].astype(int).astype(str)

    fig_season = go.Figure(go.Bar(
        x=season_best["season_str"],
        y=season_best["combined_z"],
        marker_color="#3b82f6",
        marker_line_width=0,
        width=0.5,
        # Show short name inside (or above) each bar
        text=season_best["short_name"],
        textposition="outside",
        textfont={"size": 9, "color": "#888", "family": "IBM Plex Mono, monospace"},
        customdata=season_best[["display_name", "combined_z"]].values,
        hovertemplate=(
            "<b>%{customdata[0]}</b><br>"
            "Combined z: <b>%{customdata[1]:.2f}</b>"
            "<extra></extra>"
        ),
    ))
    fig_season.update_layout(**CHART_THEME)
    fig_season.update_layout(
        xaxis={**CHART_THEME["xaxis"], "tickfont": {"family": "Inter, system-ui, sans-serif", "size": 9}},
        yaxis={**CHART_THEME["yaxis"], "visible": False},
        margin={**CHART_THEME["margin"], "t": 30},
    )
    season_label = f"Season-Best Allrounder · Highest combined z-score per season · {min_yr}-{max_yr}"

    return (
        title,
        fig_scatter, scatter_label,
        metrics,
        fig_lb,     lb_label,
        fig_depth,  depth_label,
        fig_season, season_label,
    )
