import dash
from dash import html, dcc, callback, Input, Output
import dash_bootstrap_components as dbc
import pandas as pd
import plotly.graph_objects as go

from components.metric_card import metric_card
from components.charts import CHART_THEME
from data.loader import DEL
from src.name_map import get_full_name
from src.constants import BOWLER_WICKET_KINDS

dash.register_page(__name__, path="/bowlers", name="Bowler Analytics", title="CricIQ - Bowler Analytics")

# Broad dismissal categories for the stacked bar
def _categorize_wicket(kind):
    if kind in ("caught", "caught and bowled"):
        return "caught"
    if kind == "bowled":
        return "bowled"
    if kind == "lbw":
        return "lbw"
    if kind == "stumped":
        return "stumped"
    return "other"


_WICKET_CATS   = ["caught", "bowled", "lbw", "stumped", "other"]
_WICKET_COLORS = {
    "caught":  "#3b82f6",
    "bowled":  "#22c55e",
    "lbw":     "#f97316",
    "stumped": "#ef4444",
    "other":   "#d0d0d0",
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

    html.Span(id="bowler-title", className="section-label"),

    # Row 1 - metric cards
    dbc.Row(id="bowler-metrics", className="card-row"),

    # Row 2 - death economy specialists + powerplay wicket specialists
    dbc.Row([
        dbc.Col(
            html.Div([
                html.Span(id="bowler-death-label", className="chart-card__label"),
                dcc.Graph(id="bowler-death-chart", config={"displayModeBar": False}, style={"height": "260px"}),
            ], className="chart-card"),
            width=6,
        ),
        dbc.Col(
            html.Div([
                html.Span(id="bowler-pp-label", className="chart-card__label"),
                dcc.Graph(id="bowler-pp-chart", config={"displayModeBar": False}, style={"height": "260px"}),
            ], className="chart-card"),
            width=6,
        ),
    ], className="card-row"),

    # Row 3 - wicket type breakdown + key findings
    dbc.Row([
        dbc.Col(
            html.Div([
                html.Span(id="bowler-wkt-label", className="chart-card__label"),
                dcc.Graph(id="bowler-wkt-chart", config={"displayModeBar": False}, style={"height": "380px"}),
            ], className="chart-card"),
            width=7,
        ),
        dbc.Col(
            html.Div([
                html.Span("Key Findings · 2021-26", className="chart-card__label"),
                _finding("#3b82f6", [
                    html.Strong("Caught is the dominant dismissal mode by a wide margin."),
                    " 76.1% of all bowler-credited wickets in 2021-26 were caught - "
                    "including caught-and-bowled. Bowled accounts for just 15.5%, "
                    "making edge and aerial dismissals the primary wicket-taking mechanism.",
                ]),
                _finding("#22c55e", [
                    html.Strong("Sunil Narine's 6.31 death economy is a statistical outlier."),
                    " The league avg in overs 16-20 is 10.32 - nearly 4 runs per over higher. "
                    "Bumrah (7.35) is the closest pacer, confirming that Narine's death control "
                    "is genuinely unusual for an off-spinner.",
                ]),
                _finding("#f97316", [
                    html.Strong("Death overs cost 19% more than the powerplay."),
                    " Avg economy jumps from 8.67 in overs 1-6 to 10.32 in overs 16-20. "
                    "The hardest overs to bowl are also the ones that most directly decide matches.",
                ]),
                _finding("#ef4444", [
                    html.Strong("Yuzvendra Chahal leads all bowlers with 106 wickets"),
                    " in 2021-26 - the only bowler past 100. Leg-spin is the most prolific "
                    "wicket-taking style in modern IPL, outpacing both pace and left-arm spin.",
                ]),
            ], className="chart-card findings-card"),
            width=5,
        ),
    ], className="card-row"),

    # Row 4 - powerplay economy vs death economy scatter (complete bowler quadrant chart)
    dbc.Row([
        dbc.Col(
            html.Div([
                html.Span(id="bowler-scatter-label", className="chart-card__label"),
                dcc.Graph(id="bowler-scatter-chart", config={"displayModeBar": False}, style={"height": "360px"}),
            ], className="chart-card"),
            width=12,
        ),
    ], className="card-row"),

])


@callback(
    Output("bowler-title",        "children"),
    Output("bowler-metrics",      "children"),
    Output("bowler-death-chart",  "figure"),
    Output("bowler-death-label",  "children"),
    Output("bowler-pp-chart",     "figure"),
    Output("bowler-pp-label",     "children"),
    Output("bowler-wkt-chart",    "figure"),
    Output("bowler-wkt-label",    "children"),
    Output("bowler-scatter-chart","figure"),
    Output("bowler-scatter-label","children"),
    Input("season-filter", "data"),
)
def update_bowler(season_data):
    min_yr = season_data["min"]
    max_yr = season_data["max"]

    title = (
        "Bowler Analytics · All Time (2008-2026)"
        if min_yr <= 2008
        else f"Bowler Analytics · {min_yr}-{max_yr}"
    )

    # del_f includes wides - needed for runs conceded (wides count against the bowler's economy)
    del_f = DEL[
        (DEL["season"] >= min_yr) &
        (DEL["season"] <= max_yr) &
        (~DEL["super_over"])
    ]
    # legal excludes wides - used to count balls bowled and wickets
    legal = del_f[~del_f["is_wide"]]

    # ── Bowling stats: one row per bowler x phase ────────────────────
    # Balls bowled from legal deliveries; runs from del_f (includes wide extras)
    bowl_balls = legal.groupby(["bowler", "phase"]).size().reset_index(name="balls_bowled")
    bowl_runs  = del_f.groupby(["bowler", "phase"])["total_runs"].sum().reset_index(name="runs_conceded")
    bowl_wkts  = (
        legal[legal["wicket_kind"].isin(BOWLER_WICKET_KINDS)]
        .groupby(["bowler", "phase"])
        .size()
        .reset_index(name="wickets")
    )

    bowl_phase = (
        bowl_balls
        .merge(bowl_runs,  on=["bowler", "phase"], how="left")
        .merge(bowl_wkts,  on=["bowler", "phase"], how="left")
    )
    bowl_phase["wickets"]      = bowl_phase["wickets"].fillna(0).astype(int)
    bowl_phase["runs_conceded"]= bowl_phase["runs_conceded"].fillna(0)
    # economy = runs per over (6 balls = 1 over)
    bowl_phase["economy"] = bowl_phase["runs_conceded"] / (bowl_phase["balls_bowled"] / 6)

    # ── Overall wicket totals (all phases, for cards and chart C) ────
    total_wkts = (
        legal[legal["wicket_kind"].isin(BOWLER_WICKET_KINDS)]
        .groupby("bowler")
        .size()
        .reset_index(name="wickets")
        .sort_values("wickets", ascending=False)
    )

    # ── Phase-filtered subsets (50+ balls threshold) ─────────────────
    death_q = bowl_phase[(bowl_phase["phase"] == "death")     & (bowl_phase["balls_bowled"] >= 50)].copy()
    pp_q    = bowl_phase[(bowl_phase["phase"] == "powerplay") & (bowl_phase["balls_bowled"] >= 50)].copy()

    # ── Metric cards ─────────────────────────────────────────────────
    # 1. Total qualified bowlers (50+ legal balls in any phase)
    total_balls_per_bowler = legal.groupby("bowler").size().reset_index(name="balls_bowled")
    n_qualified = int((total_balls_per_bowler["balls_bowled"] >= 50).sum())

    # 2. Avg league death economy (weighted across all 50+ death qualifiers)
    league_death_econ = (
        death_q["runs_conceded"].sum() / (death_q["balls_bowled"].sum() / 6)
    )

    # 3. Highest wicket-taker
    top_wkt_row  = total_wkts.iloc[0]
    top_wkt_name = get_full_name(top_wkt_row["bowler"])

    # 4. Best death economy (lowest) among 50+ death ball qualifiers
    best_death_row  = death_q.loc[death_q["economy"].idxmin()]
    best_death_name = get_full_name(best_death_row["bowler"])

    p_qualified   = int(min(n_qualified        / 250 * 100, 100))
    p_league_econ = int(min(league_death_econ  / 15  * 100, 100))
    p_top_wkts    = int(min(top_wkt_row["wickets"] / 150 * 100, 100))
    p_best_econ   = int(min(best_death_row["economy"] / 12 * 100, 100))

    metrics = [
        dbc.Col(metric_card(
            "Qualified Bowlers",
            str(n_qualified),
            secondary=" (50+ balls)",
            progress=p_qualified, color="blue",
        ), width=3),
        dbc.Col(metric_card(
            "Avg Death Economy",
            f"{league_death_econ:.2f}",
            secondary=" runs/over",
            progress=p_league_econ, color="orange",
        ), width=3),
        dbc.Col(metric_card(
            "Top Wicket-Taker",
            str(top_wkt_row["wickets"]),
            secondary=f" · {top_wkt_name}",
            progress=p_top_wkts, color="green",
        ), width=3),
        dbc.Col(metric_card(
            "Best Death Economy",
            f"{best_death_row['economy']:.2f}",
            secondary=f" · {best_death_name}",
            progress=p_best_econ, color="orange",
        ), width=3),
    ]

    # ── Chart A: Death economy specialists ───────────────────────────
    # Lower economy = better; sort ascending so best (lowest) appears at top
    death_top = death_q.sort_values("economy", ascending=True).head(10).reset_index(drop=True)
    death_top["display_name"] = death_top["bowler"].map(get_full_name)

    fig_death = go.Figure(go.Bar(
        x=death_top["economy"],
        y=death_top["display_name"],
        orientation="h",
        marker_color="#f97316",
        marker_line_width=0,
        width=0.5,
        text=[f"{e:.2f}  ({b}b)" for e, b in zip(death_top["economy"], death_top["balls_bowled"])],
        textposition="outside",
        textfont={"size": 9, "color": "#777", "family": "IBM Plex Mono, monospace"},
        hovertemplate="<b>%{y}</b><br>Death Economy: %{x:.2f}<extra></extra>",
    ))
    fig_death.add_vline(x=league_death_econ, line_dash="dot", line_color="#ccc", line_width=1)
    fig_death.update_layout(**CHART_THEME)
    fig_death.update_layout(
        yaxis={
            "autorange": "reversed",
            "tickmode": "array",
            "tickvals": death_top["display_name"].tolist(),
            "ticktext": death_top["display_name"].tolist(),
            "tickfont": {"family": "Inter, system-ui, sans-serif", "size": 9},
        },
        margin={**CHART_THEME["margin"], "l": 130, "r": 110},
        # x-axis range: starts at 0 and extends past the league avg line for context
        xaxis={**CHART_THEME["xaxis"], "range": [0, league_death_econ * 1.25]},
    )
    death_label = (
        f"Death Economy Specialists · Overs 16-20 · Lower = better "
        f"· Dashed = league avg {league_death_econ:.2f}"
    )

    # ── Chart B: Powerplay wicket specialists ────────────────────────
    pp_top = pp_q.sort_values("wickets", ascending=False).head(10).reset_index(drop=True)
    pp_top["display_name"] = pp_top["bowler"].map(get_full_name)

    fig_pp = go.Figure(go.Bar(
        x=pp_top["wickets"],
        y=pp_top["display_name"],
        orientation="h",
        marker_color="#3b82f6",
        marker_line_width=0,
        width=0.5,
        text=[f"{w}  ({b}b)" for w, b in zip(pp_top["wickets"], pp_top["balls_bowled"])],
        textposition="outside",
        textfont={"size": 9, "color": "#777", "family": "IBM Plex Mono, monospace"},
        hovertemplate="<b>%{y}</b><br>PP Wickets: %{x}<extra></extra>",
    ))
    fig_pp.update_layout(**CHART_THEME)
    fig_pp.update_layout(
        yaxis={
            "autorange": "reversed",
            "tickmode": "array",
            "tickvals": pp_top["display_name"].tolist(),
            "ticktext": pp_top["display_name"].tolist(),
            "tickfont": {"family": "Inter, system-ui, sans-serif", "size": 9},
        },
        margin={**CHART_THEME["margin"], "l": 130, "r": 60},
        xaxis={**CHART_THEME["xaxis"], "range": [0, pp_top["wickets"].max() * 1.35]},
    )
    pp_label = "Powerplay Wicket Specialists · Wickets in Overs 1-6 · 50+ balls bowled"

    # ── Chart C: Wicket type breakdown ───────────────────────────────
    # Top 15 overall wicket-takers; stacked percentage bar by dismissal type
    top15_bowlers = total_wkts.head(15)["bowler"].tolist()
    wkt_del = legal[
        legal["bowler"].isin(top15_bowlers) &
        legal["wicket_kind"].isin(BOWLER_WICKET_KINDS)
    ].copy()
    wkt_del["category"] = wkt_del["wicket_kind"].map(_categorize_wicket)

    # Pivot to wide format: one row per bowler, one column per category (raw counts)
    wkt_counts = (
        wkt_del.groupby(["bowler", "category"])
        .size()
        .unstack(fill_value=0)
        .reset_index()
    )
    for cat in _WICKET_CATS:
        if cat not in wkt_counts.columns:
            wkt_counts[cat] = 0

    # Convert raw counts to percentages so all bars share the same 0-100 scale
    wkt_counts["total"] = wkt_counts[_WICKET_CATS].sum(axis=1)
    for cat in _WICKET_CATS:
        wkt_counts[f"{cat}_pct"] = wkt_counts[cat] / wkt_counts["total"] * 100

    # Merge total wicket count back in to use for sorting and labeling
    wkt_counts = wkt_counts.merge(
        total_wkts[["bowler", "wickets"]], on="bowler", how="left"
    )
    wkt_counts = wkt_counts.sort_values("wickets", ascending=False).reset_index(drop=True)
    wkt_counts["display_name"] = wkt_counts["bowler"].map(get_full_name)

    fig_wkt = go.Figure()

    for cat in _WICKET_CATS:
        fig_wkt.add_trace(go.Bar(
            y=wkt_counts["display_name"].tolist(),
            x=wkt_counts[f"{cat}_pct"].tolist(),
            name=cat.title(),
            orientation="h",
            marker_color=_WICKET_COLORS[cat],
            marker_line_width=0,
            hovertemplate=(
                f"<b>%{{y}}</b><br>"
                f"{cat.title()}: <b>%{{x:.1f}}%</b>"
                f"<extra></extra>"
            ),
        ))

    # Scatter trace to show total wicket count as text after each full bar
    fig_wkt.add_trace(go.Scatter(
        x=[104] * len(wkt_counts),
        y=wkt_counts["display_name"].tolist(),
        mode="text",
        text=[f"{w}w" for w in wkt_counts["wickets"]],
        textfont={"size": 8, "color": "#888", "family": "IBM Plex Mono, monospace"},
        showlegend=False,
        hoverinfo="skip",
    ))

    fig_wkt.update_layout(**CHART_THEME)
    fig_wkt.update_layout(
        barmode="stack",
        showlegend=True,
        legend={
            "font": {"family": "Inter, system-ui, sans-serif", "size": 9, "color": "#888"},
            "bgcolor": "rgba(0,0,0,0)",
            "borderwidth": 0,
            "orientation": "h",
            "yanchor": "bottom",
            "y": 1.01,
            "xanchor": "left",
            "x": 0,
        },
        yaxis={
            "autorange": "reversed",
            "tickmode": "array",
            "tickvals": wkt_counts["display_name"].tolist(),
            "ticktext": wkt_counts["display_name"].tolist(),
            "tickfont": {"family": "Inter, system-ui, sans-serif", "size": 9},
        },
        xaxis={
            **CHART_THEME["xaxis"],
            "range": [0, 115],
            "visible": False,
        },
        margin={**CHART_THEME["margin"], "l": 130, "r": 20, "t": 28},
    )
    wkt_label = f"Wicket Type Breakdown · Top 15 Wicket-Takers · {min_yr}-{max_yr}"

    # ── Chart D: PP economy vs death economy scatter ──────────────────
    # Only bowlers with 50+ legal balls in BOTH phases qualify.
    # Lower economy = better in both axes, so "Complete Bowler" is bottom-left.
    # Analogue of the complete batsmen scatter on the batters page.
    pp_legal   = legal[legal["phase"] == "powerplay"]
    death_legal = legal[legal["phase"] == "death"]

    pp_balls   = pp_legal.groupby("bowler").size().rename("pp_balls")
    death_balls = death_legal.groupby("bowler").size().rename("death_balls")

    pp_all   = del_f[del_f["phase"] == "powerplay"]
    death_all = del_f[del_f["phase"] == "death"]

    pp_runs   = pp_all.groupby("bowler")["total_runs"].sum().rename("pp_runs")
    death_runs = death_all.groupby("bowler")["total_runs"].sum().rename("death_runs")

    scatter_df = (
        pd.concat([pp_balls, death_balls, pp_runs, death_runs], axis=1)
        .dropna()
        .query("pp_balls >= 50 and death_balls >= 50")
        .copy()
    )
    scatter_df["pp_econ"]    = scatter_df["pp_runs"]    / (scatter_df["pp_balls"]    / 6)
    scatter_df["death_econ"] = scatter_df["death_runs"] / (scatter_df["death_balls"] / 6)
    scatter_df.index.name    = "bowler"
    scatter_df                = scatter_df.reset_index()
    scatter_df["display_name"] = scatter_df["bowler"].map(get_full_name)

    # Quadrant midpoints for reference lines
    pp_med    = scatter_df["pp_econ"].median()
    death_med = scatter_df["death_econ"].median()

    fig_scatter = go.Figure()

    # Shaded quadrant backgrounds — axis is clamped to 10/12 so x_max_s/y_max_s
    # match the visible area so the shading doesn't bleed past the axis limits.
    x_min   = scatter_df["pp_econ"].min()    - 0.5
    x_max_s = 10
    y_min   = scatter_df["death_econ"].min() - 0.5
    y_max_s = 12

    for x0, x1, y0, y1, color, label, lx, ly in [
        (x_min, pp_med, y_min, death_med, "rgba(34,197,94,0.06)",   "Complete Bowler", x_min + 0.1, y_min + 0.2),
        (pp_med, x_max_s, y_min, death_med, "rgba(59,130,246,0.06)", "Death Specialist", pp_med + 0.1, y_min + 0.2),
        (x_min, pp_med, death_med, y_max_s, "rgba(249,115,22,0.06)", "PP Specialist",   x_min + 0.1, death_med + 0.2),
        (pp_med, x_max_s, death_med, y_max_s, "rgba(200,200,200,0.06)", "Expensive Both", pp_med + 0.1, death_med + 0.2),
    ]:
        fig_scatter.add_shape(type="rect", x0=x0, x1=x1, y0=y0, y1=y1,
                              fillcolor=color, line_width=0, layer="below")
        fig_scatter.add_annotation(x=lx, y=ly, text=label, showarrow=False,
                                   font={"size": 8, "color": "#555", "family": "Inter, system-ui, sans-serif"},
                                   xanchor="left")

    fig_scatter.add_vline(x=pp_med,    line_dash="dot", line_color="#e5e5e5", line_width=1)
    fig_scatter.add_hline(y=death_med, line_dash="dot", line_color="#e5e5e5", line_width=1)

    # Split into two traces: label only the "Complete Bowler" quadrant (both economies
    # below median) - the rest are hover-only to avoid crowding the chart.
    elite_mask = (scatter_df["pp_econ"] < pp_med) & (scatter_df["death_econ"] < death_med)
    elite_df   = scatter_df[elite_mask]
    rest_df    = scatter_df[~elite_mask]

    hover_tmpl = (
        "<b>%{text}</b><br>"
        "PP econ: %{x:.2f}  (%{customdata[0]} balls)<br>"
        "Death econ: %{y:.2f}  (%{customdata[1]} balls)<extra></extra>"
    )

    # Non-elite: grey markers, name only on hover
    fig_scatter.add_trace(go.Scatter(
        x=rest_df["pp_econ"],
        y=rest_df["death_econ"],
        mode="markers",
        marker={"color": "#888", "size": 6, "opacity": 0.55},
        text=rest_df["display_name"],
        customdata=list(zip(rest_df["pp_balls"], rest_df["death_balls"])),
        hovertemplate=hover_tmpl,
        showlegend=False,
    ))
    # Complete Bowler quadrant: colored + labeled
    if not elite_df.empty:
        fig_scatter.add_trace(go.Scatter(
            x=elite_df["pp_econ"],
            y=elite_df["death_econ"],
            mode="markers+text",
            marker={"color": "#22c55e", "size": 8, "opacity": 0.85},
            text=elite_df["display_name"],
            textposition="top center",
            textfont={"size": 7, "color": "#22c55e", "family": "Inter, system-ui, sans-serif"},
            customdata=list(zip(elite_df["pp_balls"], elite_df["death_balls"])),
            hovertemplate=hover_tmpl,
            showlegend=False,
        ))

    fig_scatter.update_layout(**CHART_THEME)
    fig_scatter.update_layout(
        xaxis={**CHART_THEME["xaxis"], "range": [x_min, 10], "title": {"text": "Powerplay Economy →  (lower = better)", "font": {"size": 9, "color": "#777"}}},
        yaxis={**CHART_THEME["yaxis"], "range": [y_min, 12], "title": {"text": "Death Economy →  (lower = better)", "font": {"size": 9, "color": "#777"}}},
        margin={**CHART_THEME["margin"], "l": 50, "r": 20, "t": 12, "b": 40},
    )
    n_complete = len(scatter_df[(scatter_df["pp_econ"] < pp_med) & (scatter_df["death_econ"] < death_med)])
    scatter_label = (
        f"PP Economy vs Death Economy · 50+ balls in both phases · "
        f"{n_complete} complete bowlers (below median in both) · {min_yr}-{max_yr}"
        f" · capped at PP≤10 / Death≤12"
    )

    return (
        title, metrics,
        fig_death, death_label,
        fig_pp,    pp_label,
        fig_wkt,   wkt_label,
        fig_scatter, scatter_label,
    )
