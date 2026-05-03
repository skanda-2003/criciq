import dash
from dash import html, dcc, callback, Input, Output
import dash_bootstrap_components as dbc
import pandas as pd
import plotly.graph_objects as go

from components.metric_card import metric_card
from components.charts import CHART_THEME

dash.register_page(__name__, path="/head-to-head", name="Head-to-Head", title="CricIQ - Head to Head")

# ── Load data at server start ────────────────────────────────────────
_mat = pd.read_csv("data/processed/matches.csv")
_del = pd.read_csv("data/processed/deliveries.csv")

_mat = _mat[_mat["season"] >= 2021]
_del = _del[(_del["season"] >= 2021) & (~_del["super_over"].astype(bool))]

# All teams that appear in either column
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
            html.P("vs", style={"textAlign": "center", "color": "#aaa", "fontSize": "12px", "marginTop": "7px"}),
            width=1,
        ),
        dbc.Col(
            dcc.Dropdown(id="h2h-team-b", options=[{"label": t, "value": t} for t in _TEAMS],
                         value="Chennai Super Kings", clearable=False),
            width=4,
        ),
    ], className="card-row", align="center"),

    dbc.Row(id="h2h-metrics", className="card-row"),

    dbc.Row([
        dbc.Col(html.Div(id="h2h-phase-chart", className="chart-card"), width=6),
        dbc.Col(html.Div(id="h2h-feed"),                                  width=6),
    ], className="card-row"),

])


@callback(
    Output("h2h-metrics",     "children"),
    Output("h2h-phase-chart", "children"),
    Output("h2h-feed",        "children"),
    Input("h2h-team-a", "value"),
    Input("h2h-team-b", "value"),
)
def update_h2h(team_a, team_b):
    if not team_a or not team_b or team_a == team_b:
        return [], [], html.P("Select two different teams.", style={"fontSize": "11px", "color": "#888"})

    # Matches between these two teams only
    h2h = _mat[
        (_mat["team1"].isin([team_a, team_b])) &
        (_mat["team2"].isin([team_a, team_b]))
    ]

    if h2h.empty:
        return [], [], html.P("No head-to-head matches found.", style={"fontSize": "11px", "color": "#888"})

    total  = len(h2h)
    a_wins = len(h2h[h2h["winner"] == team_a])
    b_wins = len(h2h[h2h["winner"] == team_b])

    run_margins = h2h["result_margin_runs"].dropna()
    avg_margin  = int(run_margins.mean()) if not run_margins.empty else 0

    metrics = [
        dbc.Col(metric_card("H2H Matches",             str(total),  progress=100,                                          color="blue"),   width=3),
        dbc.Col(metric_card(f"{team_a.split()[-1]} Wins", str(a_wins), progress=int(a_wins / total * 100) if total else 0, color="green"),  width=3),
        dbc.Col(metric_card(f"{team_b.split()[-1]} Wins", str(b_wins), progress=int(b_wins / total * 100) if total else 0, color="orange"), width=3),
        dbc.Col(metric_card("Avg Win Margin",          f"{avg_margin}",                                                    color="blue"),   width=3),
    ]

    # Phase run totals for each team in 1st innings of H2H matches
    match_ids = h2h["match_id"].tolist()
    h2h_del   = _del[(_del["match_id"].isin(match_ids)) & (_del["innings"] == 1)]

    phase_totals = (
        h2h_del.groupby(["batting_team", "phase"])["total_runs"]
        .sum()
        .reset_index()
    )

    fig = go.Figure()
    phase_order = ["powerplay", "middle", "death"]

    for team, tdf in phase_totals.groupby("batting_team"):
        if team not in [team_a, team_b]:
            continue
        tdf = tdf.set_index("phase").reindex(phase_order).reset_index()
        fig.add_trace(go.Bar(
            name=team.split()[-1],
            x=tdf["phase"],
            y=tdf["total_runs"],
            marker_line_width=0,
            width=0.35,
        ))

    fig.update_layout(**CHART_THEME)
    fig.update_layout(barmode="group", showlegend=True)

    phase_chart = [
        html.Span("Total Runs by Phase · 1st Innings", className="chart-card__label"),
        dcc.Graph(figure=fig, config={"displayModeBar": False}, style={"height": "220px"}),
    ]

    # Match feed — most recent first
    recent = h2h.sort_values("date", ascending=False).head(8)

    feed_items = [html.Span("Recent Matches", className="section-label")]

    for _, row in recent.iterrows():
        winner = row.get("winner", "")
        if pd.notna(row.get("result_margin_runs")) and row["result_margin_runs"] > 0:
            margin = f"{int(row['result_margin_runs'])} runs"
        elif pd.notna(row.get("result_margin_wickets")) and row["result_margin_wickets"] > 0:
            margin = f"{int(row['result_margin_wickets'])} wkts"
        else:
            margin = "–"

        accent = "#3b82f6" if winner == team_a else "#f97316"

        feed_items.append(html.Div([
            html.Div(style={
                "position": "absolute", "left": 0, "top": 0, "bottom": 0,
                "width": "3px", "backgroundColor": accent, "borderRadius": "0 2px 2px 0",
            }),
            html.Div([
                html.Div(f"{str(row.get('venue',''))[:35]} · {str(row.get('date',''))[:10]}", className="feed-row__tag"),
                html.Div(f"{winner} won", className="feed-row__title"),
            ], className="feed-row__left"),
            html.Div([
                html.Div(margin, className="feed-row__value"),
            ], className="feed-row__right"),
        ], className="feed-row"))

    return metrics, phase_chart, feed_items
