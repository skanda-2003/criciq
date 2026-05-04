import dash
from dash import html, dcc, callback, Input, Output
import dash_bootstrap_components as dbc
import pandas as pd
import plotly.graph_objects as go

from components.metric_card import metric_card
from components.charts import CHART_THEME, empty_figure
from data.loader import DEL
from src.name_map import get_full_name

dash.register_page(__name__, path="/batting", name="Batting Analytics", title="CricIQ - Batting Analytics")


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

    html.Span(id="batting-title", className="section-label"),

    # Row 1 - metric cards
    dbc.Row(id="batting-metrics", className="card-row"),

    # Row 2 - powerplay specialists + middle overs anchors
    dbc.Row([
        dbc.Col(
            html.Div([
                html.Span(id="batting-pp-label", className="chart-card__label"),
                dcc.Graph(id="batting-pp-chart", config={"displayModeBar": False}, style={"height": "260px"}),
            ], className="chart-card"),
            width=6,
        ),
        dbc.Col(
            html.Div([
                html.Span(id="batting-mid-label", className="chart-card__label"),
                dcc.Graph(id="batting-mid-chart", config={"displayModeBar": False}, style={"height": "260px"}),
            ], className="chart-card"),
            width=6,
        ),
    ], className="card-row"),

    # Row 3 - death specialists + key findings
    dbc.Row([
        dbc.Col(
            html.Div([
                html.Span(id="batting-death-label", className="chart-card__label"),
                dcc.Graph(id="batting-death-chart", config={"displayModeBar": False}, style={"height": "360px"}),
            ], className="chart-card"),
            width=5,
        ),
        dbc.Col(
            html.Div([
                html.Span("Key Findings · 2021-26", className="chart-card__label"),
                _finding("#3b82f6", [
                    html.Strong("All-phase contributors are rare."),
                    " Only 49 of 94 powerplay-qualified batters also qualify in the death phase "
                    "(50+ balls each). Most IPL batters are phase-specific - genuine all-rounders "
                    "of the bat are the exception, not the rule.",
                ]),
                _finding("#22c55e", [
                    html.Strong("Middle overs are the slowest phase."),
                    " Avg SR of 137 in overs 7-15 is lower than even the powerplay (140). "
                    "Teams shift into consolidation mode between overs 7 and 15 - "
                    "the 'filler phase' is measurable in the data.",
                ]),
                _finding("#f97316", [
                    html.Strong("Death overs carry a 22% SR premium."),
                    " League avg SR jumps from 140 in the powerplay to 171 in overs 16-20. "
                    "Role specialization and pinch-hitting are measurable, not just tactical preference.",
                ]),
                _finding("#ef4444", [
                    html.Strong("Suryavanshi is a statistical outlier."),
                    " His 225 SR across 290 balls sits 85 above the death-phase league average. "
                    "No other 2021-26 qualifier comes within 30 SR points of that gap.",
                ]),
            ], className="chart-card findings-card"),
            width=7,
        ),
    ], className="card-row"),

    # Row 4 - complete batsmen scatter (flagship chart, full width)
    dbc.Row([
        dbc.Col(
            html.Div([
                html.Span(id="batting-scatter-label", className="chart-card__label"),
                dcc.Graph(id="batting-scatter-chart", config={"displayModeBar": False}, style={"height": "420px"}),
            ], className="chart-card"),
            width=12,
        ),
    ], className="card-row"),

])


@callback(
    Output("batting-title",         "children"),
    Output("batting-metrics",       "children"),
    Output("batting-pp-chart",      "figure"),
    Output("batting-pp-label",      "children"),
    Output("batting-mid-chart",     "figure"),
    Output("batting-mid-label",     "children"),
    Output("batting-death-chart",   "figure"),
    Output("batting-death-label",   "children"),
    Output("batting-scatter-chart", "figure"),
    Output("batting-scatter-label", "children"),
    Input("season-filter", "data"),
)
def update_batting(season_data):
    min_yr = season_data["min"]
    max_yr = season_data["max"]

    title = (
        "Batting Analytics · All Time (2008-2026)"
        if min_yr <= 2008
        else f"Batting Analytics · {min_yr}-{max_yr}"
    )

    # Filter to selected window; exclude super overs throughout
    del_f = DEL[
        (DEL["season"] >= min_yr) &
        (DEL["season"] <= max_yr) &
        (~DEL["super_over"].astype(bool))
    ]
    # Wides don't count as balls faced - exclude from all per-ball stats
    legal = del_f[~del_f["is_wide"].astype(bool)]

    # ── Phase stats: one row per batter x phase ──────────────────────
    phase_stats = legal.groupby(["batter", "phase"]).agg(
        balls_faced=("batter_runs", "count"),
        runs_scored=("batter_runs", "sum"),
        fours      =("is_boundary_4", "sum"),
        sixes      =("is_boundary_6", "sum"),
        dots       =("is_dot", "sum"),
    ).reset_index()
    phase_stats["boundaries"]   = phase_stats["fours"] + phase_stats["sixes"]
    phase_stats["strike_rate"]  = phase_stats["runs_scored"] / phase_stats["balls_faced"] * 100
    phase_stats["boundary_pct"] = phase_stats["boundaries"] / phase_stats["balls_faced"] * 100

    # ── Overall stats across all phases combined ──────────────────────
    total = legal.groupby("batter").agg(
        total_balls=("batter_runs", "count"),
        total_runs =("batter_runs", "sum"),
        fours      =("is_boundary_4", "sum"),
        sixes      =("is_boundary_6", "sum"),
    ).reset_index()
    total["boundaries"]   = total["fours"] + total["sixes"]
    total["sr"]           = total["total_runs"] / total["total_balls"] * 100
    total["boundary_pct"] = total["boundaries"] / total["total_balls"] * 100
    # 50+ total balls to qualify - filters out players with tiny samples
    total_q = total[total["total_balls"] >= 50].copy()

    # ── Metric cards ──────────────────────────────────────────────────
    best_sr_row    = total_q.loc[total_q["sr"].idxmax()]
    most_runs_row  = total_q.loc[total_q["total_runs"].idxmax()]
    best_bp_row    = total_q.loc[total_q["boundary_pct"].idxmax()]
    most_balls_row = total_q.loc[total_q["total_balls"].idxmax()]

    # Progress bar denominators are elite ceilings, not theoretical maxes
    p_sr    = int(min(best_sr_row["sr"]             / 200  * 100, 100))
    p_runs  = int(min(most_runs_row["total_runs"]   / 4000 * 100, 100))
    p_bp    = int(min(best_bp_row["boundary_pct"]   / 30   * 100, 100))
    p_balls = int(min(most_balls_row["total_balls"] / 2500 * 100, 100))

    metrics = [
        dbc.Col(metric_card(
            "Best Strike Rate",
            f"{best_sr_row['sr']:.0f}",
            secondary=f" · {get_full_name(best_sr_row['batter'])}",
            progress=p_sr, color="orange",
        ), width=3),
        dbc.Col(metric_card(
            "Most Runs",
            f"{most_runs_row['total_runs']:,}",
            secondary=f" · {get_full_name(most_runs_row['batter'])}",
            progress=p_runs, color="blue",
        ), width=3),
        dbc.Col(metric_card(
            "Best Boundary %",
            f"{best_bp_row['boundary_pct']:.1f}%",
            secondary=f" · {get_full_name(best_bp_row['batter'])}",
            progress=p_bp, color="green",
        ), width=3),
        dbc.Col(metric_card(
            "Most Balls Faced",
            f"{most_balls_row['total_balls']:,}",
            secondary=f" · {get_full_name(most_balls_row['batter'])}",
            progress=p_balls, color="blue",
        ), width=3),
    ]

    # ── Chart A: Powerplay specialists ────────────────────────────────
    pp_q = phase_stats[
        (phase_stats["phase"] == "powerplay") & (phase_stats["balls_faced"] >= 50)
    ].copy()
    pp_top = pp_q.sort_values("strike_rate", ascending=False).head(10).reset_index(drop=True)
    pp_top["display_name"] = pp_top["batter"].map(get_full_name)
    # Weighted league avg: total runs / total balls across all pp qualifiers
    pp_league_sr = pp_q["runs_scored"].sum() / pp_q["balls_faced"].sum() * 100

    fig_pp = go.Figure(go.Bar(
        x=pp_top["strike_rate"],
        y=pp_top["display_name"],
        orientation="h",
        marker_color="#3b82f6",
        marker_line_width=0,
        width=0.5,
        text=[f"{sr:.0f}  ({b}b)" for sr, b in zip(pp_top["strike_rate"], pp_top["balls_faced"])],
        textposition="outside",
        textfont={"size": 9, "color": "#aaa", "family": "IBM Plex Mono, monospace"},
        hovertemplate="<b>%{y}</b><br>PP SR: %{x:.0f}<extra></extra>",
    ))
    fig_pp.add_vline(x=pp_league_sr, line_dash="dot", line_color="#ccc", line_width=1)
    fig_pp.update_layout(**CHART_THEME)
    fig_pp.update_layout(
        yaxis={
            "autorange": "reversed",
            "tickmode": "array",
            "tickvals": pp_top["display_name"].tolist(),
            "ticktext": pp_top["display_name"].tolist(),
            "tickfont": {"family": "Inter, system-ui, sans-serif", "size": 9},
        },
        margin={**CHART_THEME["margin"], "l": 130, "r": 90},
        xaxis={**CHART_THEME["xaxis"], "range": [0, 230]},
    )
    pp_label = f"Powerplay Specialists · SR in Overs 1-6 · Dashed = league avg {pp_league_sr:.0f}"

    # ── Chart B: Middle overs anchors ─────────────────────────────────
    mid_q = phase_stats[
        (phase_stats["phase"] == "middle") & (phase_stats["balls_faced"] >= 50)
    ].copy()
    mid_top = mid_q.sort_values("strike_rate", ascending=False).head(10).reset_index(drop=True)
    mid_top["display_name"] = mid_top["batter"].map(get_full_name)
    mid_league_sr = mid_q["runs_scored"].sum() / mid_q["balls_faced"].sum() * 100

    fig_mid = go.Figure(go.Bar(
        x=mid_top["strike_rate"],
        y=mid_top["display_name"],
        orientation="h",
        marker_color="#22c55e",
        marker_line_width=0,
        width=0.5,
        text=[f"{sr:.0f}  ({b}b)" for sr, b in zip(mid_top["strike_rate"], mid_top["balls_faced"])],
        textposition="outside",
        textfont={"size": 9, "color": "#aaa", "family": "IBM Plex Mono, monospace"},
        hovertemplate="<b>%{y}</b><br>Middle SR: %{x:.0f}<extra></extra>",
    ))
    fig_mid.add_vline(x=mid_league_sr, line_dash="dot", line_color="#ccc", line_width=1)
    fig_mid.update_layout(**CHART_THEME)
    fig_mid.update_layout(
        yaxis={
            "autorange": "reversed",
            "tickmode": "array",
            "tickvals": mid_top["display_name"].tolist(),
            "ticktext": mid_top["display_name"].tolist(),
            "tickfont": {"family": "Inter, system-ui, sans-serif", "size": 9},
        },
        margin={**CHART_THEME["margin"], "l": 130, "r": 90},
        xaxis={**CHART_THEME["xaxis"], "range": [0, 230]},
    )
    mid_label = f"Middle Overs Anchors · SR in Overs 7-15 · Dashed = league avg {mid_league_sr:.0f}"

    # ── Chart C: Death specialists ─────────────────────────────────────
    # Batting position is not in phase_batting.csv, so I compute it from DEL directly.
    # This is also why Chart C responds to the season filter but Charts A and B can't if
    # they were reading a pre-computed CSV - here all three read DEL, so all respond.
    death_q = phase_stats[
        (phase_stats["phase"] == "death") & (phase_stats["balls_faced"] >= 50)
    ].copy()
    avg_pos = (
        legal[legal["phase"] == "death"]
        .groupby("batter")["batting_position"]
        .mean()
        .reset_index(name="avg_position")
    )
    death_q = death_q.merge(avg_pos, on="batter", how="left")

    # Compute league avg before applying the position filter so it reflects all qualifiers
    death_league_sr = death_q["runs_scored"].sum() / death_q["balls_faced"].sum() * 100

    # Position > 5 means the batter typically enters during or just before death overs.
    # Openers who happen to survive to overs 16-20 are excluded - they are not finishers.
    specialists = (
        death_q[death_q["avg_position"] > 5]
        .sort_values("strike_rate", ascending=False)
        .head(15)
        .reset_index(drop=True)
    )
    specialists["display_name"] = specialists["batter"].map(get_full_name)

    fig_death = go.Figure(go.Bar(
        x=specialists["strike_rate"],
        y=specialists["display_name"],
        orientation="h",
        marker_color="#f97316",
        marker_line_width=0,
        width=0.5,
        text=[f"{sr:.0f}  ({b}b)" for sr, b in zip(specialists["strike_rate"], specialists["balls_faced"])],
        textposition="outside",
        textfont={"size": 9, "color": "#aaa", "family": "IBM Plex Mono, monospace"},
        hovertemplate="<b>%{y}</b><br>Death SR: %{x:.0f}<extra></extra>",
    ))
    fig_death.add_vline(x=death_league_sr, line_dash="dot", line_color="#ccc", line_width=1)
    fig_death.update_layout(**CHART_THEME)
    fig_death.update_layout(
        yaxis={
            "autorange": "reversed",
            "tickmode": "array",
            "tickvals": specialists["display_name"].tolist(),
            "ticktext": specialists["display_name"].tolist(),
            "tickfont": {"family": "Inter, system-ui, sans-serif", "size": 9},
        },
        margin={**CHART_THEME["margin"], "l": 130, "r": 90},
        xaxis={**CHART_THEME["xaxis"], "range": [0, 310]},
    )
    death_label = (
        f"Death Specialists · SR in Overs 16-20 · Avg batting position > 5 "
        f"· Dashed = league avg {death_league_sr:.0f}"
    )

    # ── Chart D: Complete batsmen scatter ─────────────────────────────
    # Players with 50+ balls in BOTH powerplay AND death qualify.
    # No position filter here - an opener who is also elite in death is genuinely interesting.
    pp_scatter = pp_q[["batter", "strike_rate", "balls_faced"]].rename(
        columns={"strike_rate": "pp_sr", "balls_faced": "pp_balls"}
    )
    # death_q already has 50+ death ball filter; use all qualifiers (not just position > 5)
    death_scatter = death_q[["batter", "strike_rate", "balls_faced"]].rename(
        columns={"strike_rate": "death_sr", "balls_faced": "death_balls"}
    )
    scatter = pp_scatter.merge(death_scatter, on="batter").reset_index(drop=True)
    scatter["display_name"] = scatter["batter"].map(get_full_name)

    # Quadrant dividers sit at the weighted league average for each phase
    pp_avg    = pp_league_sr
    death_avg = death_league_sr

    # "Complete Batsman" = above avg in both phases; label only these players
    complete_mask = (scatter["pp_sr"] >= pp_avg) & (scatter["death_sr"] >= death_avg)
    non_complete  = scatter[~complete_mask].reset_index(drop=True)
    complete      = scatter[complete_mask].reset_index(drop=True)

    fig_scatter = go.Figure()

    # Grey dots for everyone below the threshold in at least one phase
    if not non_complete.empty:
        fig_scatter.add_trace(go.Scatter(
            x=non_complete["pp_sr"],
            y=non_complete["death_sr"],
            mode="markers",
            marker={"size": 6, "color": "#d0d0d0", "line": {"width": 0}},
            customdata=non_complete[["display_name", "pp_balls", "death_balls"]].values,
            hovertemplate=(
                "<b>%{customdata[0]}</b><br>"
                "PP SR: <b>%{x:.0f}</b> (%{customdata[1]:.0f}b)<br>"
                "Death SR: <b>%{y:.0f}</b> (%{customdata[2]:.0f}b)"
                "<extra></extra>"
            ),
            showlegend=False,
        ))

    # Blue dots + name labels for "Complete Batsman" quadrant only
    if not complete.empty:
        fig_scatter.add_trace(go.Scatter(
            x=complete["pp_sr"],
            y=complete["death_sr"],
            mode="markers+text",
            text=complete["display_name"],
            textposition="top center",
            textfont={"size": 8, "color": "#111", "family": "IBM Plex Mono, monospace"},
            marker={"size": 7, "color": "#3b82f6", "line": {"width": 0}},
            customdata=complete[["display_name", "pp_balls", "death_balls"]].values,
            hovertemplate=(
                "<b>%{customdata[0]}</b><br>"
                "PP SR: <b>%{x:.0f}</b> (%{customdata[1]:.0f}b)<br>"
                "Death SR: <b>%{y:.0f}</b> (%{customdata[2]:.0f}b)"
                "<extra></extra>"
            ),
            showlegend=False,
        ))

    # Dashed reference lines marking each phase's league average
    fig_scatter.add_vline(x=pp_avg,    line_dash="dot", line_color="#ddd", line_width=1)
    fig_scatter.add_hline(y=death_avg, line_dash="dot", line_color="#ddd", line_width=1)

    fig_scatter.update_layout(**CHART_THEME)
    fig_scatter.update_layout(
        xaxis={"title": {
            "text": "Powerplay SR (Overs 1-6)",
            "font": {"family": "Inter, system-ui, sans-serif", "size": 9, "color": "#888"},
        }},
        yaxis={"title": {
            "text": "Death SR (Overs 16-20)",
            "font": {"family": "Inter, system-ui, sans-serif", "size": 9, "color": "#888"},
        }},
        annotations=[
            dict(x=0.98, y=0.98, xref="paper", yref="paper",
                 text="Complete Batsman", showarrow=False,
                 xanchor="right", yanchor="top",
                 font={"size": 9, "color": "#3b82f6", "family": "Inter, system-ui, sans-serif"}),
            dict(x=0.02, y=0.98, xref="paper", yref="paper",
                 text="Pure Finisher", showarrow=False,
                 xanchor="left", yanchor="top",
                 font={"size": 9, "color": "#f97316", "family": "Inter, system-ui, sans-serif"}),
            dict(x=0.98, y=0.02, xref="paper", yref="paper",
                 text="Pure Opener", showarrow=False,
                 xanchor="right", yanchor="bottom",
                 font={"size": 9, "color": "#22c55e", "family": "Inter, system-ui, sans-serif"}),
            dict(x=0.02, y=0.02, xref="paper", yref="paper",
                 text="Anchor", showarrow=False,
                 xanchor="left", yanchor="bottom",
                 font={"size": 9, "color": "#888", "family": "Inter, system-ui, sans-serif"}),
        ],
        margin={**CHART_THEME["margin"], "l": 50, "r": 20, "b": 40},
    )

    n_complete   = int(complete_mask.sum())
    scatter_label = (
        f"Complete Batsmen · PP SR vs Death SR · 50+ balls in each phase "
        f"· {n_complete} players above avg in both · {min_yr}-{max_yr}"
    )

    return (
        title, metrics,
        fig_pp,     pp_label,
        fig_mid,    mid_label,
        fig_death,  death_label,
        fig_scatter, scatter_label,
    )
