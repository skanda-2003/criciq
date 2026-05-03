import dash
from dash import html, dcc, callback, Input, Output
import dash_bootstrap_components as dbc
import pandas as pd
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

from components.charts import win_probability_gauge

dash.register_page(__name__, path="/simulator", name="Match Simulator", title="CricIQ - Simulator")

# ── Retrain LR model at server start ────────────────────────────────
# The saved .pkl has a scikit-learn version mismatch, so we refit here.
# Runs once on startup — takes ~2 seconds on the full dataset.
_del = pd.read_csv("data/processed/deliveries.csv")
_del2 = _del[
    (_del["season"] >= 2021) &
    (~_del["super_over"].astype(bool)) &
    (_del["innings"] == 2) &
    (_del["required_run_rate"].notna()) &
    (_del["run_rate_pressure"].notna())
].copy()

_del2["wickets_in_hand"] = 10 - _del2["cumulative_wickets"]
_del2["overs_remaining"] = 20 - _del2["over"]
_del2["won"] = (_del2["batting_team"] == _del2["match_winner"]).astype(int)

_FEATURES = ["current_run_rate", "required_run_rate", "run_rate_pressure",
             "wickets_in_hand", "overs_remaining"]
_X = _del2[_FEATURES].replace([np.inf, -np.inf], np.nan).dropna()
_y = _del2.loc[_X.index, "won"]

_scaler = StandardScaler()
_model  = LogisticRegression(max_iter=1000, random_state=42)
_model.fit(_scaler.fit_transform(_X), _y)

_TEAMS = sorted(_del["batting_team"].unique())

# ── Input field style shared across number inputs ────────────────────
_INPUT_STYLE = {
    "width":       "100%",
    "border":      "1px solid #e5e5e5",
    "borderRadius": "4px",
    "padding":     "6px 10px",
    "fontSize":    "13px",
    "fontFamily":  "Inter, system-ui, sans-serif",
    "outline":     "none",
}

# ── Layout ───────────────────────────────────────────────────────────
layout = html.Div([

    html.Span("Match Simulator · 2nd Innings Chase", className="section-label"),

    dbc.Row([

        # Left: input form
        dbc.Col(html.Div([
            html.Span("Chase Inputs", className="chart-card__label"),

            html.P("Batting Team", className="section-label", style={"marginBottom": "4px"}),
            dcc.Dropdown(id="sim-team", options=[{"label": t, "value": t} for t in _TEAMS],
                         value=_TEAMS[0], clearable=False),

            dbc.Row([
                dbc.Col([
                    html.P("Target", className="section-label", style={"marginBottom": "4px", "marginTop": "14px"}),
                    dcc.Input(id="sim-target", type="number", value=180, min=50, max=350, step=1, style=_INPUT_STYLE),
                ], width=6),
                dbc.Col([
                    html.P("Current Score", className="section-label", style={"marginBottom": "4px", "marginTop": "14px"}),
                    dcc.Input(id="sim-score", type="number", value=60, min=0, max=350, step=1, style=_INPUT_STYLE),
                ], width=6),
            ]),

            html.P(id="sim-overs-label", className="section-label", style={"marginBottom": "4px", "marginTop": "14px"}),
            dcc.Slider(id="sim-overs", min=1, max=19, step=1, value=10,
                       marks={i: str(i) for i in range(1, 20, 2)},
                       tooltip={"placement": "bottom", "always_visible": False}),

            html.P(id="sim-wickets-label", className="section-label", style={"marginBottom": "4px", "marginTop": "12px"}),
            dcc.Slider(id="sim-wickets", min=0, max=9, step=1, value=3,
                       marks={i: str(i) for i in range(10)},
                       tooltip={"placement": "bottom", "always_visible": False}),

        ], className="chart-card"), width=5),

        # Right: gauge output
        dbc.Col(html.Div([
            html.Span("Win Probability", className="chart-card__label"),
            dcc.Graph(id="sim-gauge", config={"displayModeBar": False}, style={"height": "260px"}),
            html.Div(id="sim-stats", style={"textAlign": "center"}),
        ], className="chart-card"), width=7),

    ], className="card-row"),
])


@callback(
    Output("sim-gauge",         "figure"),
    Output("sim-overs-label",   "children"),
    Output("sim-wickets-label", "children"),
    Output("sim-stats",         "children"),
    Input("sim-target",  "value"),
    Input("sim-score",   "value"),
    Input("sim-overs",   "value"),
    Input("sim-wickets", "value"),
    Input("sim-team",    "value"),
)
def update_simulator(target, score, overs_done, wickets_fallen, team):
    import traceback
    try:
        target         = target or 180
        score          = score or 0
        overs_done     = overs_done or 1
        wickets_fallen = wickets_fallen or 0

        overs_remaining = 20 - overs_done
        runs_needed     = max(target - score, 0)
        wickets_in_hand = 10 - wickets_fallen

        current_rr  = score / overs_done if overs_done > 0 else 0.0
        required_rr = runs_needed / overs_remaining if overs_remaining > 0 else 36.0
        rr_pressure = required_rr / current_rr if current_rr > 0 else 2.0

        X_new = pd.DataFrame(
            [[current_rr, required_rr, rr_pressure, wickets_in_hand, overs_remaining]],
            columns=_FEATURES,
        )
        prob  = float(_model.predict_proba(_scaler.transform(X_new))[0][1])
        gauge = win_probability_gauge(prob, title=f"{team}")

        stats = html.Span(
            f"Need {runs_needed} off {overs_remaining * 6} balls  ·  "
            f"RRR {required_rr:.2f}  ·  CRR {current_rr:.2f}",
            style={"fontSize": "11px", "color": "#888"},
        )
        return gauge, f"Overs Completed · {overs_done}", f"Wickets Fallen · {wickets_fallen}", stats

    except Exception:
        traceback.print_exc()   # full traceback in the terminal
        from components.charts import empty_figure
        return (
            empty_figure("Model error — check terminal for traceback"),
            "Overs Completed",
            "Wickets Fallen",
            html.Span("Error computing probability — see terminal.", style={"fontSize": "11px", "color": "#ef4444"}),
        )
