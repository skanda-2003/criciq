import dash
from dash import html, dcc, callback, Input, Output
import dash_bootstrap_components as dbc
import pandas as pd
import plotly.graph_objects as go

from components.metric_card import metric_card
from components.charts import CHART_THEME, empty_figure
from data.loader import DEL, MAT
from src.name_map import get_full_name

dash.register_page(__name__, path="/team", name="Team Strategy", title="CricIQ - Team Strategy")

_RENAME = {
    "Royal Challengers Bangalore": "Royal Challengers Bengaluru",
    "Rising Pune Supergiant":      "Rising Pune Supergiants",
    "Delhi Daredevils":            "Delhi Capitals",
    "Kings XI Punjab":             "Punjab Kings",
}

# Team list built from all seasons so it doesn't shrink when season filter narrows
_mat_all = MAT.copy()
for _col in ["team1", "team2"]:
    _mat_all[_col] = _mat_all[_col].replace(_RENAME)
_TEAMS = sorted(set(_mat_all["team1"].tolist()) | set(_mat_all["team2"].tolist()))

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
    "Maharashtra Cricket Association Stadium, Pune":                                          "Pune",
    "Punjab Cricket Association IS Bindra Stadium, Mohali":                                  "Mohali",
    "Himachal Pradesh Cricket Association Stadium, Dharamsala":                              "Dharamsala",
    "Dr DY Patil Sports Academy, Mumbai":                                                    "DY Patil",
    "Brabourne Stadium, Mumbai":                                                             "Brabourne",
    "Barsapara Cricket Stadium, Guwahati":                                                   "Guwahati",
}


layout = html.Div([

    html.Span(id="team-title", className="section-label"),

    # Team selector
    dbc.Row([
        dbc.Col(
            dcc.Dropdown(
                id="team-select",
                options=[{"label": t, "value": t} for t in _TEAMS],
                value="Mumbai Indians",
                clearable=False,
            ),
            width=5,
        ),
    ], className="card-row"),

    # Row 1 - metric cards
    dbc.Row(id="team-metrics", className="card-row"),

    # Row 2 - phase scoring profile + toss by venue
    dbc.Row([
        dbc.Col(
            html.Div([
                html.Span(id="team-phase-label", className="chart-card__label"),
                dcc.Graph(id="team-phase-chart", config={"displayModeBar": False}, style={"height": "240px"}),
            ], className="chart-card"),
            width=7,
        ),
        dbc.Col(
            html.Div([
                html.Span(id="team-toss-label", className="chart-card__label"),
                dcc.Graph(id="team-toss-chart", config={"displayModeBar": False}, style={"height": "240px"}),
            ], className="chart-card"),
            width=5,
        ),
    ], className="card-row"),

    # Row 3 - win rate trend + batting depth
    dbc.Row([
        dbc.Col(
            html.Div([
                html.Span(id="team-winrate-label", className="chart-card__label"),
                dcc.Graph(id="team-winrate-chart", config={"displayModeBar": False}, style={"height": "220px"}),
            ], className="chart-card"),
            width=8,
        ),
        dbc.Col(
            html.Div([
                html.Span(id="team-depth-label", className="chart-card__label"),
                dcc.Graph(id="team-depth-chart", config={"displayModeBar": False}, style={"height": "220px"}),
            ], className="chart-card"),
            width=4,
        ),
    ], className="card-row"),

])


@callback(
    Output("team-title",        "children"),
    Output("team-metrics",      "children"),
    Output("team-phase-chart",  "figure"),
    Output("team-phase-label",  "children"),
    Output("team-toss-chart",   "figure"),
    Output("team-toss-label",   "children"),
    Output("team-winrate-chart","figure"),
    Output("team-winrate-label","children"),
    Output("team-depth-chart",  "figure"),
    Output("team-depth-label",  "children"),
    Input("team-select",    "value"),
    Input("season-filter",  "data"),
)
def update_team(selected_team, season_data):
    min_yr = season_data["min"]
    max_yr = season_data["max"]

    title = (
        f"Team Strategy · {selected_team} · All Time (2008-2026)"
        if min_yr <= 2008
        else f"Team Strategy · {selected_team} · {min_yr}-{max_yr}"
    )

    # Filter + apply team renames so all name variants collapse to their current name
    mat_f = MAT[(MAT["season"] >= min_yr) & (MAT["season"] <= max_yr)].copy()
    for col in ["team1", "team2", "winner", "toss_winner"]:
        mat_f[col] = mat_f[col].replace(_RENAME)

    del_f = DEL[
        (DEL["season"] >= min_yr) &
        (DEL["season"] <= max_yr) &
        (~DEL["super_over"].astype(bool))
    ].copy()
    for col in ["batting_team", "bowling_team", "match_winner"]:
        del_f[col] = del_f[col].replace(_RENAME)

    legal = del_f[~del_f["is_wide"].astype(bool)]

    # All matches the selected team played in
    team_matches = mat_f[
        (mat_f["team1"] == selected_team) | (mat_f["team2"] == selected_team)
    ].reset_index(drop=True)

    n_total = len(team_matches)
    if n_total == 0:
        empty = empty_figure("No data for selected filters")
        return title, [], empty, "", empty, "", empty, "", empty, ""

    # ── Batting first vs chasing: determined from innings 1 in DEL ──
    # A team bats first if they appear as batting_team in innings == 1
    bat_first_ids = set(
        del_f[(del_f["batting_team"] == selected_team) & (del_f["innings"] == 1)]["match_id"].unique()
    )
    chase_ids = set(
        del_f[(del_f["batting_team"] == selected_team) & (del_f["innings"] == 2)]["match_id"].unique()
    )

    # ── Metric cards ─────────────────────────────────────────────────
    wins       = len(team_matches[team_matches["winner"] == selected_team])
    win_rate   = wins / n_total * 100

    bat_first_matches = team_matches[team_matches["match_id"].isin(bat_first_ids)]
    n_bat_first       = len(bat_first_matches)
    bat_first_wins    = len(bat_first_matches[bat_first_matches["winner"] == selected_team])
    bat_first_rate    = bat_first_wins / n_bat_first * 100 if n_bat_first > 0 else 0

    chase_matches = team_matches[team_matches["match_id"].isin(chase_ids)]
    n_chase       = len(chase_matches)
    chase_wins    = len(chase_matches[chase_matches["winner"] == selected_team])
    chase_rate    = chase_wins / n_chase * 100 if n_chase > 0 else 0

    toss_wins   = len(team_matches[team_matches["toss_winner"] == selected_team])
    toss_rate   = toss_wins / n_total * 100

    metrics = [
        dbc.Col(metric_card(
            "Overall Win Rate",
            f"{win_rate:.0f}%",
            secondary=f" ({wins}/{n_total})",
            progress=int(win_rate), color="blue",
        ), width=3),
        dbc.Col(metric_card(
            "Win Rate Batting First",
            f"{bat_first_rate:.0f}%",
            secondary=f" ({bat_first_wins}/{n_bat_first})",
            progress=int(bat_first_rate), color="green",
        ), width=3),
        dbc.Col(metric_card(
            "Win Rate Chasing",
            f"{chase_rate:.0f}%",
            secondary=f" ({chase_wins}/{n_chase})",
            progress=int(chase_rate), color="orange",
        ), width=3),
        dbc.Col(metric_card(
            "Toss Win %",
            f"{toss_rate:.0f}%",
            secondary=f" ({toss_wins}/{n_total})",
            progress=int(toss_rate), color="blue",
        ), width=3),
    ]

    # ── Chart A: Phase scoring profile vs league avg ──────────────────
    # Use del_f (includes wides) so extras count toward the innings total
    team_bat_del   = del_f[del_f["batting_team"] == selected_team]
    phases         = ["powerplay", "middle", "death"]
    phase_labels   = ["Powerplay", "Middle", "Death"]
    team_phase_avg = []
    league_phase_avg = []

    for ph in phases:
        # Team: avg runs per batting innings in this phase
        t_ph  = team_bat_del[team_bat_del["phase"] == ph]
        t_per = t_ph.groupby("match_id")["total_runs"].sum()
        team_phase_avg.append(t_per.mean() if len(t_per) > 0 else 0)

        # League: avg runs per (match, batting_team) pair in this phase
        l_ph  = del_f[del_f["phase"] == ph]
        l_per = l_ph.groupby(["match_id", "batting_team"])["total_runs"].sum()
        league_phase_avg.append(l_per.mean() if len(l_per) > 0 else 0)

    # Short name for the legend: last word of team name (e.g. "Indians", "Kings")
    short_name = selected_team.split()[-1]

    fig_phase = go.Figure([
        go.Bar(
            name=short_name,
            x=phase_labels,
            y=team_phase_avg,
            marker_color="#3b82f6",
            marker_line_width=0,
            width=0.35,
            text=[f"{v:.0f}" for v in team_phase_avg],
            textposition="outside",
            textfont={"size": 9, "color": "#777", "family": "IBM Plex Mono, monospace"},
        ),
        go.Bar(
            name="League avg",
            x=phase_labels,
            y=league_phase_avg,
            marker_color="#d0d0d0",
            marker_line_width=0,
            width=0.35,
            text=[f"{v:.0f}" for v in league_phase_avg],
            textposition="outside",
            textfont={"size": 9, "color": "#777", "family": "IBM Plex Mono, monospace"},
        ),
    ])
    fig_phase.update_layout(**CHART_THEME)
    fig_phase.update_layout(
        barmode="group",
        showlegend=True,
        yaxis={**CHART_THEME["yaxis"], "visible": False},
        xaxis={**CHART_THEME["xaxis"], "tickfont": {"family": "Inter, system-ui, sans-serif", "size": 10}},
        margin={**CHART_THEME["margin"], "t": 28, "b": 4},
    )
    phase_label = f"Phase Scoring Profile · Avg runs per innings · {selected_team} vs League"

    # ── Chart B: Toss decision preference by venue ────────────────────
    # For each venue with 3+ matches, show % of matches where team batted first
    venue_rows = []
    for venue, grp in team_matches.groupby("venue"):
        if len(grp) < 3:
            continue
        n_v       = len(grp)
        n_bf      = sum(1 for mid in grp["match_id"] if mid in bat_first_ids)
        bat_pct   = n_bf / n_v * 100
        short_v   = _VENUE_SHORT.get(venue, venue.split(",")[0][:14])
        venue_rows.append({"venue": short_v, "bat_pct": bat_pct, "n": n_v})

    if venue_rows:
        venue_df = pd.DataFrame(venue_rows).sort_values("bat_pct", ascending=True).reset_index(drop=True)
        fig_toss = go.Figure(go.Bar(
            x=venue_df["bat_pct"],
            y=venue_df["venue"],
            orientation="h",
            marker_color="#3b82f6",
            marker_line_width=0,
            width=0.5,
            text=[f"{p:.0f}%  ({n}m)" for p, n in zip(venue_df["bat_pct"], venue_df["n"])],
            textposition="outside",
            textfont={"size": 9, "color": "#777", "family": "IBM Plex Mono, monospace"},
            hovertemplate="<b>%{y}</b><br>Bat first: %{x:.0f}%<extra></extra>",
        ))
        fig_toss.add_vline(x=50, line_dash="dot", line_color="#ccc", line_width=1)
        fig_toss.update_layout(**CHART_THEME)
        fig_toss.update_layout(
            yaxis={
                "autorange": "reversed",
                "tickmode": "array",
                "tickvals": venue_df["venue"].tolist(),
                "ticktext": venue_df["venue"].tolist(),
                "tickfont": {"family": "Inter, system-ui, sans-serif", "size": 9},
            },
            margin={**CHART_THEME["margin"], "l": 80, "r": 80},
            xaxis={**CHART_THEME["xaxis"], "range": [0, 130]},
        )
    else:
        fig_toss = empty_figure("Fewer than 3 matches at any single venue")

    toss_label = (
        f"Bat-First Tendency by Venue · % of matches · 3+ matches threshold "
        f"· Dashed = 50% (even split)"
    )

    # ── Chart C: Win rate trend by season ─────────────────────────────
    season_rows = []
    for season, grp in team_matches.groupby("season"):
        n_s   = len(grp)
        w_s   = len(grp[grp["winner"] == selected_team])
        season_rows.append({"season": int(season), "win_pct": w_s / n_s * 100, "wins": w_s, "total": n_s})

    if season_rows:
        s_df = pd.DataFrame(season_rows).sort_values("season")
        fig_wr = go.Figure()
        # Shaded area under the line
        fig_wr.add_trace(go.Scatter(
            x=s_df["season"],
            y=s_df["win_pct"],
            mode="lines+markers",
            line={"color": "#3b82f6", "width": 2},
            marker={"size": 6, "color": "#3b82f6"},
            fill="tozeroy",
            fillcolor="rgba(59,130,246,0.07)",
            customdata=s_df[["wins", "total"]].values,
            hovertemplate=(
                "<b>%{x}</b><br>"
                "Win rate: <b>%{y:.0f}%</b><br>"
                "%{customdata[0]:.0f}W / %{customdata[1]:.0f}M"
                "<extra></extra>"
            ),
        ))
        fig_wr.add_hline(y=50, line_dash="dot", line_color="#ccc", line_width=1)
        fig_wr.update_layout(**CHART_THEME)
        fig_wr.update_layout(
            yaxis={**CHART_THEME["yaxis"], "range": [0, 100], "ticksuffix": "%", "nticks": 5},
            xaxis={**CHART_THEME["xaxis"], "tickformat": "d", "tickfont": {"family": "Inter, system-ui, sans-serif", "size": 9}},
            margin={**CHART_THEME["margin"], "t": 8},
        )
    else:
        fig_wr = empty_figure("No season data")

    wr_label = f"Win Rate by Season · Dashed = 50% benchmark"

    # ── Chart D: Batting depth indicator ─────────────────────────────
    # Count matches per season where batting positions 7-9 scored 20+ combined
    lower = legal[
        (legal["batting_team"] == selected_team) &
        (legal["batting_position"].isin([7, 8, 9]))
    ]
    lower_per_match = (
        lower.groupby(["match_id", "season"])["batter_runs"]
        .sum()
        .reset_index(name="lower_runs")
    )
    depth_matches = lower_per_match[lower_per_match["lower_runs"] >= 20]
    depth_per_season = depth_matches.groupby("season").size().reset_index(name="count")

    # Merge with total matches per season to compute proportion for hover
    total_per_season = team_matches.groupby("season").size().reset_index(name="total")
    depth_per_season = (
        depth_per_season
        .merge(total_per_season, on="season", how="right")
        .fillna(0)
        .sort_values("season")
    )
    depth_per_season["season_str"] = depth_per_season["season"].astype(int).astype(str)

    fig_depth = go.Figure(go.Bar(
        x=depth_per_season["season_str"],
        y=depth_per_season["count"],
        marker_color="#22c55e",
        marker_line_width=0,
        width=0.5,
        text=depth_per_season["count"].astype(int).astype(str),
        textposition="outside",
        textfont={"size": 9, "color": "#777", "family": "IBM Plex Mono, monospace"},
        customdata=depth_per_season[["count", "total"]].values,
        hovertemplate=(
            "<b>%{x}</b><br>"
            "Matches with 20+ lower-order runs: <b>%{customdata[0]:.0f}</b>"
            " of %{customdata[1]:.0f}<extra></extra>"
        ),
    ))
    fig_depth.update_layout(**CHART_THEME)
    fig_depth.update_layout(
        yaxis={**CHART_THEME["yaxis"], "visible": False},
        xaxis={**CHART_THEME["xaxis"], "tickfont": {"family": "Inter, system-ui, sans-serif", "size": 9}},
        margin={**CHART_THEME["margin"], "t": 24},
    )
    depth_label = "Batting Depth · Matches with 20+ runs from positions 7-9"

    return (
        title, metrics,
        fig_phase,  phase_label,
        fig_toss,   toss_label,
        fig_wr,     wr_label,
        fig_depth,  depth_label,
    )
