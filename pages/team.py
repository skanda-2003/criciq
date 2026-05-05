import dash
from dash import html, dcc, callback, Input, Output
import dash_bootstrap_components as dbc
import pandas as pd
import plotly.graph_objects as go

from components.metric_card import metric_card
from components.charts import CHART_THEME, empty_figure
from data.loader import MAT
from src.constants import TEAM_RENAME as _RENAME

# Pre-computed in notebooks/10_team_season_stats.ipynb
_TEAM = pd.read_csv("data/processed/team_season_stats.csv")

dash.register_page(__name__, path="/team", name="Team Strategy", title="CricIQ - Team Strategy")

# Team list built from all seasons so the dropdown doesn't shrink when the season filter narrows
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

    # Filter pre-computed CSV to this team + season window
    team_f = _TEAM[
        (_TEAM["team"] == selected_team) &
        (_TEAM["season"] >= min_yr) &
        (_TEAM["season"] <= max_yr)
    ].copy()

    n_total = int(team_f["matches"].sum())
    if n_total == 0:
        empty = empty_figure("No data for selected filters")
        return title, [], empty, "", empty, "", empty, "", empty, ""

    # MAT is still needed for Chart B (toss by venue requires venue column)
    # and for bat-first/chase win rate metric cards
    mat_f = MAT[(MAT["season"] >= min_yr) & (MAT["season"] <= max_yr)].copy()
    for col in ["team1", "team2", "winner", "toss_winner"]:
        mat_f[col] = mat_f[col].replace(_RENAME)

    team_matches = mat_f[
        (mat_f["team1"] == selected_team) | (mat_f["team2"] == selected_team)
    ].reset_index(drop=True)

    # Determine bat-first matches from MAT toss data (no DEL needed)
    # A team bats first if they won the toss and chose bat, or the opponent won and chose field
    bat_first_ids = set(
        team_matches[
            ((team_matches["toss_winner"] == selected_team) & (team_matches["toss_decision"] == "bat")) |
            ((team_matches["toss_winner"] != selected_team) & (team_matches["toss_decision"] == "field"))
        ]["match_id"]
    )
    chase_ids = set(team_matches["match_id"]) - bat_first_ids

    # ── Metric cards ─────────────────────────────────────────────────
    wins     = int(team_f["wins"].sum())
    win_rate = wins / n_total * 100

    bat_first_matches = team_matches[team_matches["match_id"].isin(bat_first_ids)]
    n_bat_first    = len(bat_first_matches)
    bat_first_wins = len(bat_first_matches[bat_first_matches["winner"] == selected_team])
    bat_first_rate = bat_first_wins / n_bat_first * 100 if n_bat_first > 0 else 0

    chase_matches = team_matches[team_matches["match_id"].isin(chase_ids)]
    n_chase    = len(chase_matches)
    chase_wins = len(chase_matches[chase_matches["winner"] == selected_team])
    chase_rate = chase_wins / n_chase * 100 if n_chase > 0 else 0

    # toss_chose_bat + toss_chose_field = total toss wins for this team
    toss_wins = int(team_f["toss_chose_bat"].sum() + team_f["toss_chose_field"].sum())
    toss_rate = toss_wins / n_total * 100

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
    # Weighted average across seasons (weight by matches played that season)
    team_pp    = (team_f["pp_avg_runs"]    * team_f["matches"]).sum() / n_total
    team_mid   = (team_f["mid_avg_runs"]   * team_f["matches"]).sum() / n_total
    team_death = (team_f["death_avg_runs"] * team_f["matches"]).sum() / n_total

    # League avg: all teams across the same season window, also weighted by matches
    league_f    = _TEAM[(_TEAM["season"] >= min_yr) & (_TEAM["season"] <= max_yr)]
    n_league    = int(league_f["matches"].sum())
    league_pp    = (league_f["pp_avg_runs"]    * league_f["matches"]).sum() / n_league
    league_mid   = (league_f["mid_avg_runs"]   * league_f["matches"]).sum() / n_league
    league_death = (league_f["death_avg_runs"] * league_f["matches"]).sum() / n_league

    phase_labels    = ["Powerplay", "Middle", "Death"]
    team_phase_avg  = [team_pp,    team_mid,   team_death]
    league_phase_avg= [league_pp,  league_mid, league_death]
    short_name      = selected_team.split()[-1]

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
    # MAT is needed here because venue is not in the pre-computed CSV
    venue_rows = []
    for venue, grp in team_matches.groupby("venue"):
        # Only show the 16 major IPL grounds that are in _VENUE_SHORT
        if venue not in _VENUE_SHORT:
            continue
        if len(grp) < 3:
            continue
        n_v     = len(grp)
        n_bf    = sum(1 for mid in grp["match_id"] if mid in bat_first_ids)
        bat_pct = n_bf / n_v * 100
        short_v = _VENUE_SHORT.get(venue, venue.split(",")[0][:14])
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
        "Bat-First Tendency by Venue · % of matches · 3+ matches threshold "
        "· Dashed = 50% (even split)"
    )

    # ── Chart C: Win rate trend by season ─────────────────────────────
    s_df = team_f[["season", "win_rate", "wins", "matches"]].sort_values("season").copy()
    s_df["win_pct"] = s_df["win_rate"] * 100

    if not s_df.empty:
        fig_wr = go.Figure()
        fig_wr.add_trace(go.Scatter(
            x=s_df["season"],
            y=s_df["win_pct"],
            mode="lines+markers",
            line={"color": "#3b82f6", "width": 2},
            marker={"size": 6, "color": "#3b82f6"},
            fill="tozeroy",
            fillcolor="rgba(59,130,246,0.07)",
            customdata=s_df[["wins", "matches"]].values,
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

    wr_label = "Win Rate by Season · Dashed = 50% benchmark"

    # ── Chart D: Batting depth by season ─────────────────────────────
    # depth_avg_runs = avg runs from batting positions 7-9 per match
    d_df = team_f[["season", "depth_avg_runs"]].sort_values("season").copy()
    d_df["season_str"] = d_df["season"].astype(int).astype(str)

    fig_depth = go.Figure(go.Bar(
        x=d_df["season_str"],
        y=d_df["depth_avg_runs"],
        marker_color="#22c55e",
        marker_line_width=0,
        width=0.5,
        text=[f"{v:.0f}" for v in d_df["depth_avg_runs"]],
        textposition="outside",
        textfont={"size": 9, "color": "#777", "family": "IBM Plex Mono, monospace"},
        hovertemplate=(
            "<b>%{x}</b><br>"
            "Avg runs from positions 7-9: <b>%{y:.1f}</b>"
            "<extra></extra>"
        ),
    ))
    fig_depth.update_layout(**CHART_THEME)
    fig_depth.update_layout(
        yaxis={**CHART_THEME["yaxis"], "visible": False},
        xaxis={**CHART_THEME["xaxis"], "tickfont": {"family": "Inter, system-ui, sans-serif", "size": 9}},
        margin={**CHART_THEME["margin"], "t": 24},
    )
    depth_label = "Batting Depth by Season · Avg runs from positions 7-9 per match"

    return (
        title, metrics,
        fig_phase,  phase_label,
        fig_toss,   toss_label,
        fig_wr,     wr_label,
        fig_depth,  depth_label,
    )
