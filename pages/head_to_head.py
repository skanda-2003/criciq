import dash
from dash import html, dcc, callback, Input, Output
import dash_bootstrap_components as dbc
import pandas as pd
import plotly.graph_objects as go

from components.metric_card import metric_card
from components.charts import CHART_THEME
from src.wp_model import predict_prob

dash.register_page(__name__, path="/head-to-head", name="Head-to-Head", title="CricIQ - Head to Head")

# ── Load data at server start ────────────────────────────────────────
_mat = pd.read_csv("data/processed/matches.csv")
_del = pd.read_csv("data/processed/deliveries.csv")

_mat = _mat[_mat["season"] >= 2021]
_del = _del[(_del["season"] >= 2021) & (~_del["super_over"].astype(bool))]

# Royal Challengers Bangalore was renamed to Royal Challengers Bengaluru before the 2023 season
_RENAME = {"Royal Challengers Bangalore": "Royal Challengers Bengaluru"}
for col in ["team1", "team2", "winner", "toss_winner"]:
    if col in _mat.columns:
        _mat[col] = _mat[col].replace(_RENAME)
for col in ["batting_team", "bowling_team", "match_winner"]:
    if col in _del.columns:
        _del[col] = _del[col].replace(_RENAME)

_TEAMS = sorted(set(_mat["team1"].tolist()) | set(_mat["team2"].tolist()))

# ── Layout ───────────────────────────────────────────────────────────
layout = html.Div([

    html.Span("Head-to-Head · 2021–2026", className="section-label"),

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

    # Row 2: phase chart + match feed
    dbc.Row([
        dbc.Col(html.Div(id="h2h-phase-chart", className="chart-card"), width=6),
        dbc.Col(html.Div(id="h2h-feed"),                                 width=6),
    ], className="card-row"),

    # Row 3: toss analysis (F) + win probability trajectory (G)
    dbc.Row([
        dbc.Col(html.Div(id="h2h-toss",    className="chart-card"), width=5),
        dbc.Col(html.Div(id="h2h-wp-traj", className="chart-card"), width=7),
    ], className="card-row"),

])


@callback(
    Output("h2h-metrics",   "children"),
    Output("h2h-phase-chart","children"),
    Output("h2h-feed",       "children"),
    Output("h2h-toss",       "children"),
    Output("h2h-wp-traj",    "children"),
    Input("h2h-team-a", "value"),
    Input("h2h-team-b", "value"),
)
def update_h2h(team_a, team_b):
    if not team_a or not team_b or team_a == team_b:
        empty = html.P("Select two different teams.",
                       style={"fontSize": "11px", "color": "#888"})
        return [], [], empty, empty, empty

    h2h = _mat[
        (_mat["team1"].isin([team_a, team_b])) &
        (_mat["team2"].isin([team_a, team_b]))
    ]

    if h2h.empty:
        empty = html.P("No head-to-head matches found.",
                       style={"fontSize": "11px", "color": "#888"})
        return [], [], empty, empty, empty

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
    h2h_del   = _del[(_del["match_id"].isin(match_ids)) & (_del["innings"] == 1)]

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
        fig_phase.add_trace(go.Bar(
            name=team.split()[-1],
            x=tdf["phase"],
            y=tdf["total_runs"],
            marker_line_width=0,
            width=0.35,
        ))

    fig_phase.update_layout(**CHART_THEME)
    fig_phase.update_layout(barmode="group", showlegend=True)

    phase_chart = [
        html.Span("Total Runs by Phase · 1st Innings", className="chart-card__label"),
        dcc.Graph(figure=fig_phase, config={"displayModeBar": False},
                  style={"height": "220px"}),
    ]

    # ── Match feed ────────────────────────────────────────────────────
    recent = h2h.sort_values("date", ascending=False).head(8)
    feed_items = [html.Span("Recent Matches", className="section-label")]

    for _, row in recent.iterrows():
        winner = row.get("winner", "")
        if pd.notna(row.get("result_margin_runs")) and row["result_margin_runs"] > 0:
            margin = f"{int(row['result_margin_runs'])} runs"
        elif pd.notna(row.get("result_margin_wickets")) and row["result_margin_wickets"] > 0:
            margin = f"{int(row['result_margin_wickets'])} wkts"
        else:
            margin = "-"

        accent = "#3b82f6" if winner == team_a else "#f97316"
        feed_items.append(html.Div([
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

    # ── Toss impact analysis (F) ──────────────────────────────────────
    # For each team, compute win rate when they won the toss vs when they didn't
    def _toss_row(team, h2h_df):
        toss_matches   = h2h_df[h2h_df["toss_winner"] == team]
        notoss_matches = h2h_df[h2h_df["toss_winner"] != team]

        n_toss   = len(toss_matches)
        n_notoss = len(notoss_matches)

        w_toss   = len(toss_matches[toss_matches["winner"] == team])
        w_notoss = len(notoss_matches[notoss_matches["winner"] == team])

        pct_toss   = int(w_toss   / n_toss   * 100) if n_toss   > 0 else None
        pct_notoss = int(w_notoss / n_notoss * 100) if n_notoss > 0 else None

        toss_str   = f"{pct_toss}%  ({w_toss}/{n_toss})"   if pct_toss   is not None else "No data"
        notoss_str = f"{pct_notoss}%  ({w_notoss}/{n_notoss})" if pct_notoss is not None else "No data"

        # Indicator: did winning the toss help this team?
        delta = (pct_toss or 0) - (pct_notoss or 0)
        arrow = "+" if delta > 5 else ("-" if delta < -5 else "~")

        return html.Div([
            html.Div(team.split()[-1], className="toss-team-name"),
            html.Div([
                html.Div([
                    html.Span("Won toss",  className="toss-label"),
                    html.Span(toss_str,    className="toss-value"),
                ], className="toss-stat"),
                html.Div([
                    html.Span("Lost toss", className="toss-label"),
                    html.Span(notoss_str,  className="toss-value"),
                ], className="toss-stat"),
                html.Div(
                    f"Toss advantage: {arrow}{abs(delta)}pp" if pct_toss is not None else "",
                    className="toss-delta",
                    style={"color": "#22c55e" if delta > 5 else ("#ef4444" if delta < -5 else "#aaa")},
                ),
            ]),
        ], className="toss-team-block")

    toss_section = [
        html.Span("Toss Impact", className="chart-card__label"),
        _toss_row(team_a, h2h),
        html.Hr(style={"border": "none", "borderTop": "1px solid #f0f0f0", "margin": "10px 0"}),
        _toss_row(team_b, h2h),
    ]

    # ── Win probability trajectory - most recent H2H match (G) ───────
    # Find the most recent match between these two teams that has 2nd innings data
    recent_match = h2h.sort_values("date", ascending=False).iloc[0]
    mid          = recent_match["match_id"]

    inn2 = _del[
        (_del["match_id"] == mid) &
        (_del["innings"] == 2) &
        (_del["required_run_rate"].notna()) &
        (_del["run_rate_pressure"].notna())
    ].copy()

    if inn2.empty:
        wp_traj = [
            html.Span("Win Probability Trajectory", className="chart-card__label"),
            html.P("No 2nd innings data for this match.",
                   style={"fontSize": "11px", "color": "#888", "marginTop": "12px"}),
        ]
    else:
        inn2["wickets_in_hand"] = 10 - inn2["cumulative_wickets"]
        inn2["overs_remaining"] = 20 - inn2["over"]

        # Apply model to every ball to get ball-by-ball win probability
        # Each ball is one row - vectorised predict_proba call for speed
        from src.wp_model import FEATURES, model as _wpm, scaler as _wps
        import numpy as np

        feat_df = inn2[["current_run_rate", "required_run_rate", "run_rate_pressure",
                         "wickets_in_hand", "overs_remaining"]].copy()
        feat_df = feat_df.replace([np.inf, -np.inf], np.nan).dropna()

        probs = _wpm.predict_proba(_wps.transform(feat_df))[:, 1]

        # Use feat_df.index to select the exact rows that survived .dropna()
        # (NaN rows are dropped; this keeps hover labels aligned with probs)
        inn2_clean   = inn2.loc[feat_df.index].reset_index(drop=True)
        seq          = list(range(1, len(probs) + 1))
        batting_team = inn2_clean["batting_team"].iloc[0]
        match_winner = inn2_clean["match_winner"].iloc[0] if inn2_clean["match_winner"].notna().any() else "Unknown"

        hover_labels = [
            f"Over {int(r['over'])}, Ball {int(r['ball_in_over'])}"
            for _, r in inn2_clean.iterrows()
        ]

        # Color: blue if batting team won, orange if they lost
        won       = batting_team == match_winner
        line_color = "#3b82f6" if won else "#f97316"
        fill_color = "rgba(59,130,246,0.08)" if won else "rgba(249,115,22,0.08)"

        fig_wp = go.Figure()
        fig_wp.add_hline(y=0.5, line_dash="dash", line_color="#e5e5e5", line_width=1)
        fig_wp.add_trace(go.Scatter(
            x=seq,
            y=probs,
            mode="lines",
            line={"color": line_color, "width": 1.5},
            fill="tozeroy",
            fillcolor=fill_color,
            showlegend=False,
            hovertemplate="%{text}: <b>%{y:.1%}</b><extra></extra>",
            text=hover_labels,
        ))

        result_color = "#3b82f6" if won else "#f97316"
        result_text  = f"{batting_team.split()[-1]} {'won' if won else 'lost'}"
        venue_short  = str(recent_match.get("venue", ""))[:30]
        date_short   = str(recent_match.get("date", ""))[:10]

        fig_wp.update_layout(**CHART_THEME)
        fig_wp.update_layout(
            xaxis={**CHART_THEME["xaxis"], "title": {"text": "Ball", "font": {"size": 9, "color": "#aaa"}}},
            yaxis={**CHART_THEME["yaxis"], "tickformat": ".0%", "range": [0, 1], "nticks": 5},
            margin={**CHART_THEME["margin"], "l": 40},
        )

        wp_traj = [
            html.Span(
                f"Win Probability · {batting_team.split()[-1]} batting · {venue_short} · {date_short}",
                className="chart-card__label",
            ),
            dcc.Graph(figure=fig_wp, config={"displayModeBar": False},
                      style={"height": "220px"}),
            html.Div(
                result_text,
                style={"textAlign": "right", "fontSize": "10px", "color": result_color,
                       "fontFamily": "IBM Plex Mono, monospace", "marginTop": "4px"},
            ),
        ]

    return metrics, phase_chart, feed_items, toss_section, wp_traj
