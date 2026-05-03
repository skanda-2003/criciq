import dash
from dash import html, dcc, callback, Input, Output
import dash_bootstrap_components as dbc
import pandas as pd
import plotly.graph_objects as go

from components.charts import win_probability_gauge, CHART_THEME
from src.wp_model import predict_prob, FEATURES

dash.register_page(__name__, path="/simulator", name="Match Simulator", title="CricIQ - Simulator")

# ── Load team list at server start ───────────────────────────────────
# The model itself is trained in src/wp_model.py and cached there - importing
# it above is all that's needed. No re-training happens here.
_del   = pd.read_csv("data/processed/deliveries.csv")
_TEAMS = sorted(_del["batting_team"].dropna().unique())

# ── Input field style ────────────────────────────────────────────────
_INPUT_STYLE = {
    "width":        "100%",
    "border":       "1px solid #e5e5e5",
    "borderRadius": "4px",
    "padding":      "6px 10px",
    "fontSize":     "12px",
    "fontFamily":   "Inter, system-ui, sans-serif",
    "outline":      "none",
}

# ── Layout ───────────────────────────────────────────────────────────
layout = html.Div([

    html.Span("Match Simulator · 2nd Innings Chase", className="section-label"),

    # Row 1: inputs (left) + gauge (right)
    dbc.Row([

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

            html.P(id="sim-overs-label",   className="section-label", style={"marginBottom": "4px", "marginTop": "14px"}),
            dcc.Slider(id="sim-overs",   min=1, max=19, step=1, value=10,
                       marks={i: str(i) for i in range(1, 20, 2)},
                       tooltip={"placement": "bottom", "always_visible": False}),

            html.P(id="sim-wickets-label", className="section-label", style={"marginBottom": "4px", "marginTop": "12px"}),
            dcc.Slider(id="sim-wickets", min=0, max=9, step=1, value=3,
                       marks={i: str(i) for i in range(10)},
                       tooltip={"placement": "bottom", "always_visible": False}),

        ], className="chart-card"), width=5),

        dbc.Col(html.Div([
            html.Span("Win Probability", className="chart-card__label"),
            dcc.Graph(id="sim-gauge", config={"displayModeBar": False}, style={"height": "240px"}),
            html.Div(id="sim-stats", style={"textAlign": "center"}),
        ], className="chart-card"), width=7),

    ], className="card-row"),

    # Row 2: projected win probability trajectory (H)
    dbc.Row([
        dbc.Col(html.Div([
            html.Span(
                "Projected Win Probability · If current run rate is maintained",
                className="chart-card__label",
            ),
            dcc.Graph(id="sim-trajectory", config={"displayModeBar": False}, style={"height": "200px"}),
        ], className="chart-card"), width=12),
    ], className="card-row"),

])


@callback(
    Output("sim-gauge",        "figure"),
    Output("sim-trajectory",   "figure"),
    Output("sim-overs-label",  "children"),
    Output("sim-wickets-label","children"),
    Output("sim-stats",        "children"),
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
        score          = score  or 0
        overs_done     = overs_done or 1
        wickets_fallen = wickets_fallen or 0

        overs_remaining = 20 - overs_done
        runs_needed     = max(target - score, 0)
        wickets_in_hand = 10 - wickets_fallen

        current_rr  = score / overs_done if overs_done > 0 else 0.0
        required_rr = runs_needed / overs_remaining if overs_remaining > 0 else 36.0
        rr_pressure = required_rr / current_rr if current_rr > 0 else 2.0

        # Current win probability (shown on the gauge)
        prob  = predict_prob(current_rr, required_rr, rr_pressure, wickets_in_hand, overs_remaining)
        gauge = win_probability_gauge(prob, title=team)

        stats = html.Span(
            f"Need {runs_needed} off {overs_remaining * 6} balls  ·  "
            f"RRR {required_rr:.2f}  ·  CRR {current_rr:.2f}",
            style={"fontSize": "11px", "color": "#888",
                   "fontFamily": "IBM Plex Mono, monospace"},
        )

        # ── Projected trajectory (H) ──────────────────────────────────
        # For each over from the current position to over 20, project forward
        # assuming the team continues at current_rr with no further wickets.
        # This answers: "if nothing changes, where is our win prob heading?"
        overs_x = []
        probs_y = []

        for future_over in range(overs_done, 21):
            extra_overs    = future_over - overs_done
            proj_score     = score + current_rr * extra_overs
            proj_needed    = max(target - proj_score, 0)
            proj_or        = 20 - future_over

            if proj_needed <= 0:
                # Team has already reached the target at this projected over
                p = 1.0
            elif proj_or == 0:
                # Last ball - either got there or didn't
                p = 1.0 if proj_needed <= 0 else 0.0
            else:
                proj_req_rr  = proj_needed / proj_or
                proj_pressure = proj_req_rr / current_rr if current_rr > 0 else 2.0
                p = predict_prob(current_rr, proj_req_rr, proj_pressure,
                                 wickets_in_hand, proj_or)

            overs_x.append(future_over)
            probs_y.append(p)

        fig_traj = go.Figure()

        # Reference line at 50% - the toss-up line
        fig_traj.add_hline(y=0.5, line_dash="dash", line_color="#e5e5e5", line_width=1)

        # Dashed extension for projected future overs, solid dot at the current state
        fig_traj.add_trace(go.Scatter(
            x=overs_x[1:],
            y=probs_y[1:],
            mode="lines",
            line={"color": "#3b82f6", "width": 1.5, "dash": "dot"},
            name="Projected",
            showlegend=False,
        ))
        # Current state highlighted as a solid marker
        fig_traj.add_trace(go.Scatter(
            x=[overs_done],
            y=[prob],
            mode="markers",
            marker={"color": "#3b82f6", "size": 8},
            name="Now",
            showlegend=False,
            hovertemplate=f"Over {overs_done}: <b>{prob:.1%}</b><extra>Current state</extra>",
        ))

        fig_traj.update_layout(**CHART_THEME)
        fig_traj.update_layout(
            xaxis={**CHART_THEME["xaxis"], "range": [overs_done - 0.5, 20.5],
                   "title": {"text": "Over", "font": {"size": 9, "color": "#aaa"}}},
            yaxis={**CHART_THEME["yaxis"], "tickformat": ".0%", "range": [0, 1],
                   "nticks": 5},
            margin={**CHART_THEME["margin"], "l": 40},
        )

        return (
            gauge, fig_traj,
            f"Overs Completed · {overs_done}",
            f"Wickets Fallen · {wickets_fallen}",
            stats,
        )

    except Exception:
        traceback.print_exc()
        from components.charts import empty_figure
        err_fig = empty_figure("Model error - check terminal")
        return (
            err_fig, err_fig,
            "Overs Completed",
            "Wickets Fallen",
            html.Span("Error - see terminal.", style={"fontSize": "11px", "color": "#ef4444"}),
        )
