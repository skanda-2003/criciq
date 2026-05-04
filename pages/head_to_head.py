import dash
from dash import html, dcc, callback, Input, Output
import dash_bootstrap_components as dbc
import pandas as pd
import plotly.graph_objects as go

from components.metric_card import metric_card
from components.charts import CHART_THEME
from src.wp_model import predict_prob
from data.loader import DEL, MAT

dash.register_page(__name__, path="/head-to-head", name="Head-to-Head", title="CricIQ - Head to Head")

# ── Static reference data ────────────────────────────────────────────
_RENAME = {"Royal Challengers Bangalore": "Royal Challengers Bengaluru"}

# Build team list from the full MAT (all seasons) so the dropdown works for
# both 2021-26 and all-time mode without missing historical franchises
_mat_all = MAT.copy()
for _col in ["team1", "team2"]:
    _mat_all[_col] = _mat_all[_col].replace(_RENAME)
_TEAMS = sorted(set(_mat_all["team1"].tolist()) | set(_mat_all["team2"].tolist()))

# ── Layout ───────────────────────────────────────────────────────────
layout = html.Div([

    html.Span(id="h2h-title", className="section-label"),

    dbc.Row([
        dbc.Col(
            dcc.Dropdown(id="h2h-team-a", options=[{"label": t, "value": t} for t in _TEAMS],
                         value="Mumbai Indians", clearable=False),
            width=4,
        ),
        dbc.Col(
            html.P("vs", style={"textAlign": "center", "color": "#aaa",
                                "fontSize": "11px", "marginTop": "7px"}),
            width=1,
        ),
        dbc.Col(
            dcc.Dropdown(id="h2h-team-b", options=[{"label": t, "value": t} for t in _TEAMS],
                         value="Chennai Super Kings", clearable=False),
            width=4,
        ),
    ], className="card-row", align="center"),

    # Row 1: summary record cards
    dbc.Row(id="h2h-metrics", className="card-row"),

    # Row 2: phase chart + match feed (feed is scrollable, no full-page scroll needed)
    dbc.Row([
        dbc.Col(html.Div(id="h2h-phase-chart", className="chart-card"), width=6),
        dbc.Col(html.Div(id="h2h-feed"),                                 width=6),
    ], className="card-row"),

    # Row 3: toss analysis + win probability trajectory
    dbc.Row([
        dbc.Col(html.Div(id="h2h-toss", className="chart-card"), width=5),
        dbc.Col(html.Div([
            # Match picker sits above the chart - selecting a match re-renders the WP line
            dcc.Dropdown(
                id="h2h-match-picker",
                placeholder="Select a match...",
                clearable=False,
                style={"marginBottom": "10px"},
            ),
            html.Div(id="h2h-wp-traj", className="chart-card"),
        ]), width=7),
    ], className="card-row"),

])


@callback(
    Output("h2h-title",        "children"),
    Output("h2h-metrics",      "children"),
    Output("h2h-phase-chart",  "children"),
    Output("h2h-feed",         "children"),
    Output("h2h-toss",         "children"),
    Output("h2h-match-picker", "options"),
    Output("h2h-match-picker", "value"),
    Input("h2h-team-a",    "value"),
    Input("h2h-team-b",    "value"),
    Input("season-filter", "data"),
)
def update_h2h(team_a, team_b, season_data):
    min_yr = season_data["min"]
    max_yr = season_data["max"]

    # Filter to the selected season window and apply team rename
    mat_f = MAT[(MAT["season"] >= min_yr) & (MAT["season"] <= max_yr)].copy()
    del_f = DEL[
        (DEL["season"] >= min_yr) & (DEL["season"] <= max_yr) &
        (~DEL["super_over"].astype(bool))
    ].copy()

    for col in ["team1", "team2", "winner", "toss_winner"]:
        if col in mat_f.columns:
            mat_f[col] = mat_f[col].replace(_RENAME)
    for col in ["batting_team", "bowling_team", "match_winner"]:
        if col in del_f.columns:
            del_f[col] = del_f[col].replace(_RENAME)

    title = "Head-to-Head · All Time (2008-2026)" if min_yr <= 2008 else f"Head-to-Head · {min_yr}-{max_yr}"

    if not team_a or not team_b or team_a == team_b:
        empty = html.P("Select two different teams.", style={"fontSize": "11px", "color": "#888"})
        return title, [], [], empty, empty, [], None

    h2h = mat_f[
        (mat_f["team1"].isin([team_a, team_b])) &
        (mat_f["team2"].isin([team_a, team_b]))
    ]

    if h2h.empty:
        empty = html.P("No head-to-head matches found.", style={"fontSize": "11px", "color": "#888"})
        return title, [], [], empty, empty, [], None

    # ── Summary record cards ─────────────────────────────────────────
    total  = len(h2h)
    a_wins = len(h2h[h2h["winner"] == team_a])
    b_wins = len(h2h[h2h["winner"] == team_b])

    run_margins = h2h["result_margin_runs"].dropna()
    avg_margin  = int(run_margins.mean()) if not run_margins.empty else 0

    metrics = [
        dbc.Col(metric_card("H2H Matches",             str(total),
                            progress=100,                                          color="blue"),   width=3),
        dbc.Col(metric_card(f"{team_a.split()[-1]} Wins", str(a_wins),
                            progress=int(a_wins / total * 100) if total else 0,   color="green"),  width=3),
        dbc.Col(metric_card(f"{team_b.split()[-1]} Wins", str(b_wins),
                            progress=int(b_wins / total * 100) if total else 0,   color="orange"), width=3),
        dbc.Col(metric_card("Avg Win Margin",          f"{avg_margin}",
                            color="blue"),                                                          width=3),
    ]

    # ── Phase run totals chart ────────────────────────────────────────
    match_ids = h2h["match_id"].tolist()
    h2h_del   = del_f[(del_f["match_id"].isin(match_ids)) & (del_f["innings"] == 1)]

    phase_totals = (
        h2h_del.groupby(["batting_team", "phase"])["total_runs"]
        .sum()
        .reset_index()
    )

    fig_phase = go.Figure()
    phase_order = ["powerplay", "middle", "death"]

    for team, tdf in phase_totals.groupby("batting_team"):
        if team not in [team_a, team_b]:
            continue
        tdf = tdf.set_index("phase").reindex(phase_order).reset_index()
        # Explicit color: team_a always blue, team_b always orange - color doesn't
        # swap when the dropdown order changes
        color = "#3b82f6" if team == team_a else "#f97316"
        fig_phase.add_trace(go.Bar(
            name=team.split()[-1],
            x=tdf["phase"],
            y=tdf["total_runs"],
            marker_color=color,
            marker_line_width=0,
            width=0.35,
        ))

    fig_phase.update_layout(**CHART_THEME)
    fig_phase.update_layout(barmode="group", showlegend=True)

    phase_chart = [
        html.Span("Total Runs by Phase · 1st Innings", className="chart-card__label"),
        dcc.Graph(figure=fig_phase, config={"displayModeBar": False}, style={"height": "200px"}),
    ]

    # ── Match feed (scrollable) ───────────────────────────────────────
    # All matches sorted newest first; container shows ~5 rows then scrolls
    sorted_h2h = h2h.sort_values("date", ascending=False)
    feed_rows  = []

    for _, row in sorted_h2h.iterrows():
        winner = row.get("winner", "")
        if pd.notna(row.get("result_margin_runs")) and row["result_margin_runs"] > 0:
            margin = f"{int(row['result_margin_runs'])} runs"
        elif pd.notna(row.get("result_margin_wickets")) and row["result_margin_wickets"] > 0:
            margin = f"{int(row['result_margin_wickets'])} wkts"
        else:
            margin = "-"

        accent = "#3b82f6" if winner == team_a else "#f97316"
        feed_rows.append(html.Div([
            html.Div(style={
                "position": "absolute", "left": 0, "top": 0, "bottom": 0,
                "width": "3px", "backgroundColor": accent, "borderRadius": "0 2px 2px 0",
            }),
            html.Div([
                html.Div(f"{str(row.get('venue',''))[:35]} · {str(row.get('date',''))[:10]}",
                         className="feed-row__tag"),
                html.Div(f"{winner} won", className="feed-row__title"),
            ], className="feed-row__left"),
            html.Div([html.Div(margin, className="feed-row__value")], className="feed-row__right"),
        ], className="feed-row"))

    feed = [
        html.Span("Recent Matches", className="section-label"),
        html.Div(feed_rows, className="h2h-feed-scroll"),
    ]

    # ── Toss impact ──────────────────────────────────────────────────
    def _toss_block(label, wins, total, color):
        # One mini stat block: label, "X wins from Y matches", progress bar, win%.
        # Returns "No data" block if total is 0 to avoid division errors.
        if total == 0:
            return html.Div([
                html.Div(label, className="toss-block__label"),
                html.Div("No data", className="toss-block__no-data"),
            ], className="toss-block")

        pct = int(wins / total * 100)
        return html.Div([
            html.Div(label, className="toss-block__label"),
            html.Div([
                html.Span(str(wins), className="toss-block__wins"),
                html.Span(f" wins / {total}", className="toss-block__denom"),
            ]),
            html.Div(
                html.Div(style={"width": f"{pct}%", "height": "100%",
                                "backgroundColor": color, "borderRadius": "2px"}),
                className="toss-block__bar-track",
            ),
            html.Div(f"{pct}% win rate", className="toss-block__pct"),
        ], className="toss-block")

    def _toss_section(team, h2h_df):
        toss_matches   = h2h_df[h2h_df["toss_winner"] == team]
        notoss_matches = h2h_df[h2h_df["toss_winner"] != team]

        n_toss   = len(toss_matches)
        n_notoss = len(notoss_matches)
        w_toss   = len(toss_matches[toss_matches["winner"] == team])
        w_notoss = len(notoss_matches[notoss_matches["winner"] == team])

        # Split toss wins by what the team chose to do
        toss_bat   = toss_matches[toss_matches["toss_decision"] == "bat"]
        toss_field = toss_matches[toss_matches["toss_decision"] == "field"]
        w_bat      = len(toss_bat[toss_bat["winner"] == team])
        w_field    = len(toss_field[toss_field["winner"] == team])

        return html.Div([
            html.Div(team.split()[-1], className="toss-team-name"),
            # Top row: did winning/losing the toss affect match outcome?
            html.Div([
                _toss_block("WON TOSS",  w_toss,   n_toss,         "#3b82f6"),
                _toss_block("LOST TOSS", w_notoss, n_notoss,        "#888"),
            ], className="toss-grid"),
            # Sub-header explains the bottom row is a breakdown of toss wins only
            html.Div("When they won the toss, they chose to...", className="toss-decision-header"),
            # Bottom row: of the toss wins, how did each decision play out?
            html.Div([
                _toss_block("BAT FIRST",   w_bat,   len(toss_bat),   "#22c55e"),
                _toss_block("FIELD FIRST", w_field, len(toss_field),  "#f97316"),
            ], className="toss-grid"),
        ], className="toss-team-block")

    toss_section = [
        html.Span("Toss Impact", className="chart-card__label"),
        _toss_section(team_a, h2h),
        html.Hr(style={"border": "none", "borderTop": "1px solid #f0f0f0", "margin": "10px 0"}),
        _toss_section(team_b, h2h),
    ]

    # ── Match picker options ─────────────────────────────────────────
    # Build one dropdown entry per H2H match, sorted newest first.
    # The value stored is match_id (an integer) - the WP callback uses it to look up deliveries.
    sorted_for_picker = h2h.sort_values("date", ascending=False)
    match_options = []
    for _, row in sorted_for_picker.iterrows():
        t1    = row["team1"].split()[-1]
        t2    = row["team2"].split()[-1]
        date  = str(row.get("date",  ""))[:10]
        venue = str(row.get("venue", ""))[:28]
        label = f"{t1} vs {t2} · {date} · {venue}"
        match_options.append({"label": label, "value": row["match_id"]})

    # Default to the most recent match so the chart is never blank on load
    default_match = match_options[0]["value"] if match_options else None

    return title, metrics, phase_chart, feed, toss_section, match_options, default_match


@callback(
    Output("h2h-wp-traj", "children"),
    Input("h2h-match-picker", "value"),
    Input("h2h-team-a",       "value"),
    Input("h2h-team-b",       "value"),
    Input("season-filter",    "data"),
)
def update_wp_trajectory(match_id, team_a, team_b, season_data):
    # This callback owns the WP chart. It fires whenever the match picker changes,
    # which happens either from a user selection or when update_h2h sets a new default.
    if not match_id:
        return [html.P("Select a match above to see its win probability trajectory.",
                       style={"fontSize": "11px", "color": "#888", "marginTop": "12px"})]

    min_yr = season_data["min"]
    max_yr = season_data["max"]

    # Re-filter from global DataFrames - same pattern as every other callback
    mat_f = MAT[(MAT["season"] >= min_yr) & (MAT["season"] <= max_yr)].copy()
    del_f = DEL[
        (DEL["season"] >= min_yr) & (DEL["season"] <= max_yr) &
        (~DEL["super_over"].astype(bool))
    ].copy()

    for col in ["team1", "team2", "winner", "toss_winner"]:
        if col in mat_f.columns:
            mat_f[col] = mat_f[col].replace(_RENAME)
    for col in ["batting_team", "bowling_team", "match_winner"]:
        if col in del_f.columns:
            del_f[col] = del_f[col].replace(_RENAME)

    # Grab the match row so we have venue + date for the chart title
    match_rows = mat_f[mat_f["match_id"] == match_id]
    if match_rows.empty:
        return [html.P("Match data not found.", style={"fontSize": "11px", "color": "#888"})]
    match_row = match_rows.iloc[0]

    # 2nd innings only - WP model is chase-only (1st innings has no required_run_rate)
    inn2 = del_f[
        (del_f["match_id"] == match_id) &
        (del_f["innings"] == 2) &
        (del_f["required_run_rate"].notna()) &
        (del_f["run_rate_pressure"].notna())
    ].copy()

    if inn2.empty:
        return [
            html.Span("Win Probability Trajectory", className="chart-card__label"),
            html.P("No 2nd innings data for this match.",
                   style={"fontSize": "11px", "color": "#888", "marginTop": "12px"}),
        ]

    inn2["wickets_in_hand"] = 10 - inn2["cumulative_wickets"]
    inn2["overs_remaining"] = 20 - inn2["over"]

    from src.wp_model import model as _wpm, scaler as _wps
    import numpy as np

    feat_df = inn2[["current_run_rate", "required_run_rate", "run_rate_pressure",
                     "wickets_in_hand", "overs_remaining"]].copy()
    feat_df = feat_df.replace([np.inf, -np.inf], np.nan).dropna()

    probs = _wpm.predict_proba(_wps.transform(feat_df))[:, 1]

    inn2_clean   = inn2.loc[feat_df.index].reset_index(drop=True)
    seq          = list(range(1, len(probs) + 1))
    batting_team = inn2_clean["batting_team"].iloc[0]
    match_winner = (inn2_clean["match_winner"].iloc[0]
                    if inn2_clean["match_winner"].notna().any() else "Unknown")

    hover_labels = [
        f"Over {int(r['over'])}, Ball {int(r['ball_in_over'])}"
        for _, r in inn2_clean.iterrows()
    ]

    won        = batting_team == match_winner
    line_color = "#3b82f6" if won else "#f97316"
    fill_color = "rgba(59,130,246,0.08)" if won else "rgba(249,115,22,0.08)"

    fig_wp = go.Figure()
    fig_wp.add_hline(y=0.5, line_dash="dash", line_color="#e5e5e5", line_width=1)
    fig_wp.add_trace(go.Scatter(
        x=seq, y=probs, mode="lines",
        line={"color": line_color, "width": 1.5},
        fill="tozeroy", fillcolor=fill_color,
        showlegend=False,
        hovertemplate="%{text}: <b>%{y:.1%}</b><extra></extra>",
        text=hover_labels,
    ))

    result_color = "#3b82f6" if won else "#f97316"
    result_text  = f"{batting_team.split()[-1]} {'won' if won else 'lost'}"
    venue_short  = str(match_row.get("venue", ""))[:30]
    date_short   = str(match_row.get("date",  ""))[:10]

    fig_wp.update_layout(**CHART_THEME)
    fig_wp.update_layout(
        xaxis={**CHART_THEME["xaxis"], "title": {"text": "Ball", "font": {"size": 9, "color": "#aaa"}}},
        yaxis={**CHART_THEME["yaxis"], "tickformat": ".0%", "range": [0, 1], "nticks": 5},
        margin={**CHART_THEME["margin"], "l": 40},
    )

    return [
        html.Span(
            f"Win Probability · {batting_team.split()[-1]} batting · {venue_short} · {date_short}",
            className="chart-card__label",
        ),
        dcc.Graph(figure=fig_wp, config={"displayModeBar": False}, style={"height": "200px"}),
        html.Div(
            result_text,
            style={"textAlign": "right", "fontSize": "10px", "color": result_color,
                   "fontFamily": "IBM Plex Mono, monospace", "marginTop": "4px"},
        ),
    ]
