import dash
from dash import html, dcc, callback, Input, Output
import dash_bootstrap_components as dbc
import plotly.graph_objects as go

from components.charts import win_probability_gauge, CHART_THEME
from src.wp_model import predict_prob, FEATURES
from data.loader import DEL

dash.register_page(__name__, path="/simulator", name="Match Simulator", title="CricIQ - Simulator")

# ── Team name normalisation ───────────────────────────────────────────
# Several franchises have been renamed or have a spelling variant in Cricsheet.
# Map every old name to the current canonical name so the dropdown has no duplicates
# and the historical lookup works correctly regardless of which era a match is from.
_TEAM_ALIASES = {
    "Royal Challengers Bangalore": "Royal Challengers Bengaluru",
    "Rising Pune Supergiant":      "Rising Pune Supergiants",
    "Delhi Daredevils":            "Delhi Capitals",
    "Kings XI Punjab":             "Punjab Kings",
}

def _norm_team(name: str) -> str:
    return _TEAM_ALIASES.get(name, name)

_TEAMS = sorted({_norm_team(t) for t in DEL["batting_team"].dropna().unique()})

# ── Pre-compute chase-state lookup table ─────────────────────────────
# For each over in each 2nd innings, take the first legal ball as the
# over-entry state (ball_in_over == 1). Compute three match keys:
#   rn     = runs still needed to win
#   wih    = wickets in hand (10 - cumulative_wickets)
#   ov_rem = overs remaining (21 - over, since over is 1-indexed)
# batting_team is normalised so historical records for renamed franchises
# (e.g. Delhi Daredevils + Delhi Capitals) are combined under the current name.
_CHASE_STATES = (
    DEL[
        (DEL["innings"] == 2) &
        (~DEL["super_over"].astype(bool)) &
        (DEL["target_runs"].notna()) &
        (DEL["ball_in_over"] == 1)
    ]
    .assign(
        rn          = lambda d: d["target_runs"] - d["cumulative_runs"],
        wih         = lambda d: 10 - d["cumulative_wickets"],
        ov_rem      = lambda d: 21 - d["over"],
        batting_won = lambda d: d["match_winner"] == d["batting_team"],
        team        = lambda d: d["batting_team"].map(_norm_team),
    )
    [["rn", "wih", "ov_rem", "batting_won", "team"]]
    .reset_index(drop=True)
)

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
            dcc.Slider(id="sim-overs",   min=1, max=20, step=1, value=10,
                       marks={i: str(i) for i in range(1, 21, 2)},
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

    # Row 3: what-if scenario cards - one predict_prob call per scenario
    dbc.Row([
        dbc.Col(html.Div([
            html.Span("Lose 1 Wicket Now", className="chart-card__label"),
            html.Div(id="sim-whatif-wicket"),
        ], className="chart-card"), width=4),
        dbc.Col(html.Div([
            html.Span("Score a Boundary Now", className="chart-card__label"),
            html.Div(id="sim-whatif-boundary"),
        ], className="chart-card"), width=4),
        dbc.Col(html.Div([
            html.Span("Dot Ball Now", className="chart-card__label"),
            html.Div(id="sim-whatif-dot"),
        ], className="chart-card"), width=4),
    ], className="card-row"),

    # Row 4: historical base rate - how often did teams in a similar situation win?
    dbc.Row([
        dbc.Col(html.Div(id="sim-base-rate", className="chart-card"), width=12),
    ], className="card-row"),

])


def _whatif_content(scenario_prob, current_prob):
    """Return the inner content (prob + delta) for a what-if card."""
    delta = scenario_prob - current_prob
    delta_color = "#22c55e" if delta > 0 else "#ef4444" if delta < 0 else "#888"
    delta_sign  = "+" if delta > 0 else ""
    return html.Div([
        html.Div(f"{scenario_prob:.0%}", className="whatif-card__prob"),
        # delta color is computed per-render so inline style is allowed per the design rules
        html.Div(
            f"{delta_sign}{delta * 100:.0f}pp vs current",
            className="whatif-card__delta",
            style={"color": delta_color},
        ),
    ])


@callback(
    Output("sim-gauge",           "figure"),
    Output("sim-trajectory",      "figure"),
    Output("sim-overs-label",     "children"),
    Output("sim-wickets-label",   "children"),
    Output("sim-stats",           "children"),
    Output("sim-whatif-wicket",   "children"),
    Output("sim-whatif-boundary", "children"),
    Output("sim-whatif-dot",      "children"),
    Output("sim-base-rate",       "children"),
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

        # Guard: if the batting team has already reached/exceeded the target, the
        # chase is over. Showing a gauge here is meaningless - show a clear message instead.
        if score >= target:
            from components.charts import empty_figure
            won_fig = empty_figure("")
            won_msg = html.Div(
                "Target already reached - this team has won.",
                style={"fontSize": "12px", "color": "#22c55e", "textAlign": "center",
                       "fontFamily": "Inter, system-ui, sans-serif", "padding": "20px 0"},
            )
            no_text  = html.Span("")
            return (
                won_fig, won_fig,
                f"Overs Completed · {overs_done}",
                f"Wickets Fallen · {wickets_fallen}",
                won_msg, no_text, no_text, no_text, no_text,
            )

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

        # ── What-if probabilities (computed before the chart so trajectories can use them) ──

        # Lose 1 wicket: same score/overs, one fewer wicket in hand
        wih_wicket    = max(0, wickets_in_hand - 1)
        prob_wicket   = predict_prob(current_rr, required_rr, rr_pressure, wih_wicket, overs_remaining)

        # Score a boundary: score += 4, overs_done unchanged (mid-over), recompute rates
        score_b       = score + 4
        crr_b         = score_b / overs_done if overs_done > 0 else 0.0
        rrr_b         = max(target - score_b, 0) / overs_remaining if overs_remaining > 0 else 36.0
        pressure_b    = rrr_b / crr_b if crr_b > 0 else 2.0
        prob_boundary = predict_prob(crr_b, rrr_b, pressure_b, wickets_in_hand, overs_remaining)

        # Dot ball: 1 ball consumed (1/6 over), score unchanged, required_rr rises
        or_dot        = max(overs_remaining - 1 / 6, 0.01)
        rrr_dot       = runs_needed / or_dot
        pressure_dot  = rrr_dot / current_rr if current_rr > 0 else 2.0
        prob_dot      = predict_prob(current_rr, rrr_dot, pressure_dot, wickets_in_hand, or_dot)

        # ── Projected trajectory (H) ──────────────────────────────────
        # For each over from the current position to over 20, project forward
        # assuming the team continues at current_rr with no further wickets.
        overs_x            = []
        probs_y            = []
        probs_wicket_traj  = []
        probs_boundary_traj = []
        probs_dot_traj     = []

        for i, future_over in enumerate(range(overs_done, 21)):
            extra_overs = future_over - overs_done
            proj_or     = 20 - future_over

            # ── Baseline: current state, maintained CRR ───────────────
            proj_score  = score + current_rr * extra_overs
            proj_needed = max(target - proj_score, 0)
            if proj_needed <= 0:
                p = 1.0
            elif proj_or == 0:
                p = 0.0
            else:
                rr  = proj_needed / proj_or
                pr  = rr / current_rr if current_rr > 0 else 2.0
                p   = predict_prob(current_rr, rr, pr, wickets_in_hand, proj_or)
            overs_x.append(future_over)
            probs_y.append(p)

            # ── Wicket scenario: same CRR, one fewer wicket ───────────
            proj_needed_w = max(target - proj_score, 0)
            if proj_needed_w <= 0:
                pw = 1.0
            elif proj_or == 0:
                pw = 0.0
            else:
                rr_w = proj_needed_w / proj_or
                pr_w = rr_w / current_rr if current_rr > 0 else 2.0
                pw   = predict_prob(current_rr, rr_w, pr_w, wih_wicket, proj_or)
            probs_wicket_traj.append(pw)

            # ── Boundary scenario: higher CRR from the 4 extra runs ───
            proj_score_b  = score_b + crr_b * extra_overs
            proj_needed_b = max(target - proj_score_b, 0)
            if proj_needed_b <= 0:
                pb = 1.0
            elif proj_or == 0:
                pb = 0.0
            else:
                rr_b = proj_needed_b / proj_or
                pr_b = rr_b / crr_b if crr_b > 0 else 2.0
                pb   = predict_prob(crr_b, rr_b, pr_b, wickets_in_hand, proj_or)
            probs_boundary_traj.append(pb)

            # ── Dot ball scenario: same score, but first point uses or_dot ──
            # The first iteration has one ball already wasted; subsequent overs are normal.
            proj_needed_d = max(target - proj_score, 0)
            proj_or_d     = or_dot if i == 0 else proj_or
            if proj_needed_d <= 0:
                pd = 1.0
            elif proj_or_d <= 0:
                pd = 0.0
            else:
                rr_d = proj_needed_d / proj_or_d
                pr_d = rr_d / current_rr if current_rr > 0 else 2.0
                pd   = predict_prob(current_rr, rr_d, pr_d, wickets_in_hand, proj_or_d)
            probs_dot_traj.append(pd)

        # ── Build trajectory chart ─────────────────────────────────────
        fig_traj = go.Figure()

        # Background zones: blue above 50% (chasing team ahead), orange below (behind)
        fig_traj.add_hrect(y0=0.5, y1=1.0, fillcolor="rgba(59,130,246,0.05)", line_width=0)
        fig_traj.add_hrect(y0=0.0, y1=0.5, fillcolor="rgba(249,115,22,0.05)",  line_width=0)

        # 50/50 reference line with a small right-side label
        fig_traj.add_hline(
            y=0.5, line_dash="dash", line_color="#d0d0d0", line_width=1,
            annotation_text="50/50",
            annotation_font={"size": 8, "color": "#aaa"},
            annotation_position="right",
        )

        # Vertical "you are here" line at the current over
        fig_traj.add_vline(x=overs_done, line_color="#e5e5e5", line_width=1, line_dash="dot")

        # What-if scenario trajectories - faint colored lines showing how paths diverge
        fig_traj.add_trace(go.Scatter(
            x=overs_x, y=probs_boundary_traj,
            mode="lines",
            line={"color": "rgba(34,197,94,0.55)", "width": 1, "dash": "dot"},
            showlegend=False,
            hovertemplate="+ Boundary: <b>%{y:.0%}</b> at over %{x}<extra></extra>",
        ))
        fig_traj.add_trace(go.Scatter(
            x=overs_x, y=probs_dot_traj,
            mode="lines",
            line={"color": "rgba(249,115,22,0.55)", "width": 1, "dash": "dot"},
            showlegend=False,
            hovertemplate="Dot ball: <b>%{y:.0%}</b> at over %{x}<extra></extra>",
        ))
        fig_traj.add_trace(go.Scatter(
            x=overs_x, y=probs_wicket_traj,
            mode="lines",
            line={"color": "rgba(239,68,68,0.55)", "width": 1, "dash": "dot"},
            showlegend=False,
            hovertemplate="- Wicket: <b>%{y:.0%}</b> at over %{x}<extra></extra>",
        ))

        # Main projected trajectory - more prominent than the what-if lines
        fig_traj.add_trace(go.Scatter(
            x=overs_x, y=probs_y,
            mode="lines",
            line={"color": "#3b82f6", "width": 2, "dash": "dot"},
            showlegend=False,
            hovertemplate="Projected: <b>%{y:.0%}</b> at over %{x}<extra></extra>",
        ))

        # Current state - solid marker on top of all lines
        fig_traj.add_trace(go.Scatter(
            x=[overs_done], y=[prob],
            mode="markers",
            marker={"color": "#3b82f6", "size": 9},
            showlegend=False,
            hovertemplate=f"Over {overs_done}: <b>{prob:.1%}</b><extra>Now</extra>",
        ))

        # Probability label directly above the current state dot
        fig_traj.add_annotation(
            x=overs_done, y=prob,
            text=f"<b>{prob:.0%}</b>",
            showarrow=False,
            yshift=12,
            font={"family": "IBM Plex Mono, monospace", "size": 9, "color": "#3b82f6"},
        )

        fig_traj.update_layout(**CHART_THEME)
        fig_traj.update_layout(
            # Always span the full 20 overs so you can see where in the innings you are
            xaxis={
                **CHART_THEME["xaxis"],
                "range": [0.5, 20.5],
                "title": {"text": "Over", "font": {"size": 9, "color": "#aaa"}},
            },
            yaxis={**CHART_THEME["yaxis"], "tickformat": ".0%", "range": [0, 1], "nticks": 5},
            margin={**CHART_THEME["margin"], "l": 40},
        )

        # ── Historical base rate (team-specific) ─────────────────────
        # Filter to the selected team so the number reflects that franchise's
        # actual chasing record, not the league average.
        # This is what makes the team dropdown meaningful - the model probability
        # is team-agnostic, but this number is not.
        norm_team = _norm_team(team)
        similar   = _CHASE_STATES[_CHASE_STATES["team"] == norm_team]
        matched   = similar[
            (similar["rn"]     >= runs_needed     - 10) &
            (similar["rn"]     <= runs_needed     + 10) &
            (similar["wih"]    >= wickets_in_hand - 1)  &
            (similar["wih"]    <= wickets_in_hand + 1)  &
            (similar["ov_rem"] >= overs_remaining - 2)  &
            (similar["ov_rem"] <= overs_remaining + 2)
        ]
        n = len(matched)
        if n > 0:
            win_pct = matched["batting_won"].mean()
            base_rate = [
                html.Span(f"Historical Context · {norm_team}", className="chart-card__label"),
                html.Div([
                    html.Span(f"In {n}", className="base-rate__value"),
                    html.Span(
                        " similar chasing situations (±10 runs, ±1 wicket, ±2 overs), ",
                        className="base-rate__text",
                    ),
                    html.Span(norm_team, className="base-rate__text"),
                    html.Span(" won ", className="base-rate__text"),
                    html.Span(f"{win_pct:.0%}", className="base-rate__value"),
                ]),
            ]
        else:
            base_rate = [
                html.Span(f"Historical Context · {norm_team}", className="chart-card__label"),
                html.Span(
                    "No matching historical situations for this team",
                    className="base-rate__text",
                ),
            ]

        return (
            gauge, fig_traj,
            f"Overs Completed · {overs_done}",
            f"Wickets Fallen · {wickets_fallen}",
            stats,
            _whatif_content(prob_wicket,   prob),
            _whatif_content(prob_boundary, prob),
            _whatif_content(prob_dot,      prob),
            base_rate,
        )

    except Exception:
        traceback.print_exc()
        from components.charts import empty_figure
        err_fig  = empty_figure("Model error - check terminal")
        err_text = html.Span("Error", style={"fontSize": "11px", "color": "#ef4444"})
        return (
            err_fig, err_fig,
            "Overs Completed",
            "Wickets Fallen",
            html.Span("Error - see terminal.", style={"fontSize": "11px", "color": "#ef4444"}),
            err_text, err_text, err_text, err_text,
        )
