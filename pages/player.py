import dash
from dash import html, dcc, callback, Input, Output
import dash_bootstrap_components as dbc
import pandas as pd
import plotly.graph_objects as go

from components.metric_card import metric_card
from components.charts import CHART_THEME
from src.name_map import get_full_name as _display_name
from data.loader import DEL

dash.register_page(__name__, path="/player", name="Player Deep-Dive", title="CricIQ - Player")

# ── Per-player pre-computed data (matchups + cluster stay 2021-26) ───
_matchups     = pd.read_csv("data/processed/bowler_matchups.csv")
_profiles     = pd.read_csv("data/processed/batsman_profiles.csv")
_impact       = pd.read_csv("data/processed/player_impact_season.csv")
_impact_match = pd.read_csv("data/processed/player_impact_match.csv")

PHASE_ORDER  = ["powerplay", "middle", "death"]
PHASE_COLORS = {"powerplay": "#3b82f6", "middle": "#22c55e", "death": "#f97316"}

# ── Pre-compute league averages for both season windows ──────────────
# Runs once at startup. The callback picks the right dict based on the store.
# League avg SR is weighted: total batter_runs / total legal balls, for players
# with 50+ balls in that phase (same threshold as the player leaderboards).
def _compute_league_avgs(del_legal):
    avgs = {}
    for ph in PHASE_ORDER:
        ph_del     = del_legal[del_legal["phase"] == ph]
        per_player = ph_del.groupby("batter").size()
        qualified  = per_player[per_player >= 50].index
        q          = ph_del[ph_del["batter"].isin(qualified)]
        if len(q) > 0:
            avgs[ph] = q["batter_runs"].sum() / len(q) * 100
    return avgs


_DEL_RECENT_LEGAL  = DEL[
    (DEL["season"] >= 2021) & (~DEL["super_over"].astype(bool)) & (~DEL["is_wide"].astype(bool))
]
_DEL_ALLTIME_LEGAL = DEL[
    (~DEL["super_over"].astype(bool)) & (~DEL["is_wide"].astype(bool))
]

# Include wides for bowling economy (wide extras count against the bowler's economy)
_DEL_RECENT_ALL  = DEL[(DEL["season"] >= 2021) & (~DEL["super_over"].astype(bool))]
_DEL_ALLTIME_ALL = DEL[~DEL["super_over"].astype(bool)]

_LEAGUE_AVG_SR_RECENT  = _compute_league_avgs(_DEL_RECENT_LEGAL)
_LEAGUE_AVG_SR_ALLTIME = _compute_league_avgs(_DEL_ALLTIME_LEGAL)


def _compute_league_bowl_avgs(del_all, del_legal):
    """League avg economy per phase for bowlers with 50+ legal balls in that phase."""
    avgs = {}
    for ph in PHASE_ORDER:
        ph_legal         = del_legal[del_legal["phase"] == ph]
        ph_all           = del_all[del_all["phase"] == ph]
        per_bowler_balls = ph_legal.groupby("bowler").size()
        qualified        = per_bowler_balls[per_bowler_balls >= 50].index
        if qualified.empty:
            continue
        runs_per_bowler  = ph_all[ph_all["bowler"].isin(qualified)].groupby("bowler")["total_runs"].sum()
        balls_per_bowler = per_bowler_balls[per_bowler_balls.index.isin(qualified)]
        econ_per_bowler  = runs_per_bowler / (balls_per_bowler / 6)
        avgs[ph]         = econ_per_bowler.mean()
    return avgs


_LEAGUE_AVG_ECON_RECENT  = _compute_league_bowl_avgs(_DEL_RECENT_ALL, _DEL_RECENT_LEGAL)
_LEAGUE_AVG_ECON_ALLTIME = _compute_league_bowl_avgs(_DEL_ALLTIME_ALL, _DEL_ALLTIME_LEGAL)

# Player dropdown: union of batting-qualified (50+ balls faced in any phase)
# and bowling-qualified (50+ legal balls bowled total). Without this union,
# pure bowlers like Bumrah and Chahal are invisible in the dropdown even
# though they have hundreds of deliveries in the dataset.
_bat_phase_counts  = _DEL_RECENT_LEGAL.groupby(["batter", "phase"]).size().reset_index(name="balls")
_bat_players       = set(_bat_phase_counts[_bat_phase_counts["balls"] >= 50]["batter"].unique())
_bowl_counts       = _DEL_RECENT_LEGAL.groupby("bowler").size()
_bowl_players      = set(_bowl_counts[_bowl_counts >= 50].index)
_players           = sorted(_bat_players | _bowl_players)


def _compute_overall_bat_avgs(del_legal, bat_players):
    """
    League-wide overall SR, boundary%, and dot% for batting-qualified players.
    Used to compute the +/- vs avg delta shown in the player page metric cards.
    """
    q = del_legal[del_legal["batter"].isin(bat_players)]
    if len(q) == 0:
        return {"sr": 0.0, "bpct": 0.0, "dpct": 0.0}
    balls       = len(q)
    boundaries  = (q["is_boundary_4"].astype(bool) | q["is_boundary_6"].astype(bool)).sum()
    dots        = q["is_dot"].astype(bool).sum()
    return {
        "sr":   q["batter_runs"].sum() / balls * 100,
        "bpct": boundaries / balls * 100,
        "dpct": dots / balls * 100,
    }


_LEAGUE_OVERALL_RECENT  = _compute_overall_bat_avgs(_DEL_RECENT_LEGAL,  _bat_players)
_LEAGUE_OVERALL_ALLTIME = _compute_overall_bat_avgs(_DEL_ALLTIME_LEGAL, _bat_players)

# Cluster archetype labels from k-means output in notebook 03
# Roles loaded from data/processed/player_roles.csv - edit that file to fix any
# misclassifications (e.g. bowlers who faced 50+ balls but are not allrounders).
# The data-driven fallback handles any player not yet in the file.
_roles_df = pd.read_csv("data/processed/player_roles.csv")
_ROLES     = dict(zip(_roles_df["player"], _roles_df["role"]))


def _player_role(p):
    """Returns 'batter', 'bowler', or 'allrounder'. Reads from player_roles.csv first."""
    if p in _ROLES:
        return _ROLES[p]
    # Fallback for players added after the file was last generated
    is_bat  = p in _bat_players
    is_bowl = p in _bowl_players
    if is_bat and is_bowl:
        return "allrounder"
    elif is_bowl:
        return "bowler"
    return "batter"


_CLUSTER_LABELS = {
    0: ("Consistent Striker", "#22c55e"),
    1: ("Aggressive Hitter",  "#f97316"),
    2: ("Steady Builder",     "#888888"),
    3: ("Power Hitter",       "#3b82f6"),
}

# ── Layout ───────────────────────────────────────────────────────────
layout = html.Div([

    html.Span(id="player-title", className="section-label"),

    # Row 1: primary player dropdown + compare dropdown + cluster badge
    dbc.Row([
        dbc.Col(
            dcc.Dropdown(
                id="player-select",
                options=[{"label": _display_name(p), "value": p} for p in _players],
                value=_players[0],
                clearable=False,
                searchable=True,
            ),
            width=4,
        ),
        dbc.Col(
            dcc.Dropdown(
                id="player-compare",
                options=[{"label": _display_name(p), "value": p} for p in _players],
                placeholder="Compare with...",
                clearable=True,
                searchable=True,
            ),
            width=4,
        ),
        dbc.Col(
            html.Div(id="player-cluster-badge"),
            width="auto",
            className="d-flex align-items-center",
        ),
        dbc.Col(
            html.Div(id="player-cv-badge"),
            width="auto",
            className="d-flex align-items-center",
        ),
    ], className="card-row"),

    # Row 2: summary metric cards
    dcc.Loading(type="circle", color="#3b82f6",
                children=dbc.Row(id="player-metrics", className="card-row")),

    # Row 3: season-by-season (left) + matchup chart with toggle (right)
    dbc.Row([
        dbc.Col(dcc.Loading(type="circle", color="#3b82f6",
                            children=html.Div(id="player-season-chart", className="chart-card")), width=6),
        dbc.Col(html.Div([
            dcc.RadioItems(
                id="matchup-metric",
                options=[
                    {"label": "Dismissal %", "value": "dismissal_prob"},
                    {"label": "Strike Rate",  "value": "strike_rate"},
                    {"label": "Boundary %",   "value": "boundary_rate"},
                ],
                value="dismissal_prob",
                className="matchup-toggle",
            ),
            dcc.Loading(type="circle", color="#3b82f6",
                        children=html.Div(id="player-matchup-chart", className="chart-card")),
        ]), width=6),
    ], className="card-row"),

    # Row 3b: comparison stats - only visible when player-compare is set
    dbc.Row(id="player-compare-stats", className="card-row"),

    # Row 4: impact score trend (left) + phase SR chart (right)
    dbc.Row([
        dbc.Col(dcc.Loading(type="circle", color="#3b82f6",
                            children=html.Div(id="player-impact-chart", className="chart-card")), width=6),
        dbc.Col(dcc.Loading(type="circle", color="#3b82f6",
                            children=html.Div(id="player-phase-chart", className="chart-card")), width=6),
    ], className="card-row"),

    # Bowling section - only rendered when the player has bowled 50+ legal balls
    dcc.Loading(type="circle", color="#3b82f6",
                children=html.Div(id="player-bowl-section")),

])


@callback(
    Output("player-title",          "children"),
    Output("player-metrics",        "children"),
    Output("player-phase-chart",    "children"),
    Output("player-matchup-chart",  "children"),
    Output("player-cluster-badge",  "children"),
    Output("player-cv-badge",       "children"),
    Output("player-impact-chart",   "children"),
    Output("player-season-chart",   "children"),
    Output("player-compare-stats",  "children"),
    Output("player-bowl-section",   "children"),
    Input("player-select",   "value"),
    Input("season-filter",   "data"),
    Input("matchup-metric",  "value"),
    Input("player-compare",  "value"),
)
def update_player(player, season_data, matchup_metric, player_compare):
    min_yr = season_data["min"]
    max_yr = season_data["max"]

    # Legal balls for this player in the selected window (wides excluded throughout)
    player_legal = DEL[
        (DEL["batter"]     == player) &
        (DEL["season"]     >= min_yr) &
        (DEL["season"]     <= max_yr) &
        (~DEL["super_over"].astype(bool)) &
        (~DEL["is_wide"]   .astype(bool))
    ]

    # League averages for the selected window
    league_avgs    = _LEAGUE_AVG_SR_RECENT if min_yr >= 2021 else _LEAGUE_AVG_SR_ALLTIME
    overall_avgs   = _LEAGUE_OVERALL_RECENT if min_yr >= 2021 else _LEAGUE_OVERALL_ALLTIME

    title = "Player Deep-Dive · All Time (2008-2026)" if min_yr <= 2008 else f"Player Deep-Dive · {min_yr}-{max_yr}"

    # ── Metric cards ─────────────────────────────────────────────────
    total_balls      = len(player_legal)
    total_runs       = int(player_legal["batter_runs"].sum())
    total_boundaries = int(
        (player_legal["is_boundary_4"].astype(bool) | player_legal["is_boundary_6"].astype(bool)).sum()
    )
    total_dots = int(player_legal["is_dot"].astype(bool).sum())

    sr   = round(total_runs / total_balls * 100, 1) if total_balls > 0 else 0
    bpct = round(total_boundaries / total_balls * 100, 1) if total_balls > 0 else 0
    dpct = round(total_dots       / total_balls * 100, 1) if total_balls > 0 else 0

    # Compute deltas vs league average for the SR, boundary%, and dot% cards.
    # Format as "+14 vs avg" or "-3 vs avg" so the card is self-interpreting.
    def _delta_str(player_val, avg_val):
        d = player_val - avg_val
        return f"{d:+.0f} vs avg"

    sr_delta   = _delta_str(sr,   overall_avgs["sr"])   if total_balls > 0 else None
    bpct_delta = _delta_str(bpct, overall_avgs["bpct"]) if total_balls > 0 else None
    dpct_delta = _delta_str(dpct, overall_avgs["dpct"]) if total_balls > 0 else None

    # ── Roles and compare player stats ───────────────────────────────
    # Computed early so every section (metric cards, charts, compare row) can branch on them.
    role_a = _player_role(player)
    role_b = _player_role(player_compare) if player_compare else None

    name_a = f"{_display_name(player)} ({role_a.title()})"
    c_sr = c_bpct = c_dpct = c_runs = c_balls = c_4s = c_6s = 0
    name_b = None
    compare_legal = None
    if player_compare:
        compare_legal = DEL[
            (DEL["batter"]     == player_compare) &
            (DEL["season"]     >= min_yr) &
            (DEL["season"]     <= max_yr) &
            (~DEL["super_over"].astype(bool)) &
            (~DEL["is_wide"]   .astype(bool))
        ]
        c_balls = len(compare_legal)
        c_runs  = int(compare_legal["batter_runs"].sum())
        c_sr    = round(c_runs / c_balls * 100, 1) if c_balls > 0 else 0
        c_bpct  = round(
            (compare_legal["is_boundary_4"].astype(bool) | compare_legal["is_boundary_6"].astype(bool)).sum()
            / c_balls * 100, 1
        ) if c_balls > 0 else 0
        c_dpct  = round(compare_legal["is_dot"].astype(bool).sum() / c_balls * 100, 1) if c_balls > 0 else 0
        c_4s    = int(compare_legal["is_boundary_4"].astype(bool).sum())
        c_6s    = int(compare_legal["is_boundary_6"].astype(bool).sum())
        name_b  = f"{_display_name(player_compare)} ({role_b.title()})"

    # Bowling stats for comparison (computed when at least one player is a bowler/allrounder)
    WKT_KINDS_BOWL = {"caught", "bowled", "lbw", "caught and bowled", "stumped", "hit wicket"}
    a_bowl = b_bowl = None

    def _bowl_cmp_stats(p):
        """Returns bowl comparison dict for player p in the selected window."""
        all_d  = DEL[(DEL["bowler"] == p) & (DEL["season"] >= min_yr) & (DEL["season"] <= max_yr) &
                     (~DEL["super_over"].astype(bool))]
        legal  = all_d[~all_d["is_wide"].astype(bool)]
        balls  = len(legal)
        if balls < 10:
            return {"wickets": "—", "economy": "—", "dot_pct": "—", "balls": 0}
        wkts   = int(legal[legal["wicket_kind"].isin(WKT_KINDS_BOWL)].shape[0])
        econ   = round(all_d["total_runs"].sum() / (balls / 6), 2)
        dot_pc = round(legal["is_dot"].astype(bool).sum() / balls * 100, 1)
        return {"wickets": wkts, "economy": econ, "dot_pct": f"{dot_pc}%", "balls": balls}

    if player_compare:
        cmp_has_bowl = (role_a in ("bowler", "allrounder")) or (role_b in ("bowler", "allrounder"))
        if cmp_has_bowl:
            a_bowl = _bowl_cmp_stats(player)
            b_bowl = _bowl_cmp_stats(player_compare)

    # cmp_type determines which stats to show in the comparison cards
    cmp_type = None
    if player_compare:
        a_bats  = role_a in ("batter", "allrounder")
        a_bowls = role_a in ("bowler", "allrounder")
        b_bats  = role_b in ("batter", "allrounder")
        b_bowls = role_b in ("bowler", "allrounder")
        both_bat  = a_bats  and b_bats
        both_bowl = a_bowls and b_bowls
        if both_bat and not (a_bowls or b_bowls):
            cmp_type = "bat"
        elif both_bowl and not (a_bats or b_bats):
            cmp_type = "bowl"
        else:
            cmp_type = "mixed"

    # Precompute 4s and 6s for primary player (used in compare stats row)
    total_4s = int(player_legal["is_boundary_4"].astype(bool).sum())
    total_6s = int(player_legal["is_boundary_6"].astype(bool).sum())

    # ── Consistency score ─────────────────────────────────────────────
    # CV (coefficient of variation) = std / mean of match-level impact scores.
    # Lower CV = more consistent match-to-match output.
    match_imp = _impact_match[
        (_impact_match["player"] == player) &
        (_impact_match["season"] >= min_yr) &
        (_impact_match["season"] <= max_yr)
    ]
    if len(match_imp) >= 3 and match_imp["impact_score"].mean() != 0:
        cv = match_imp["impact_score"].std() / abs(match_imp["impact_score"].mean())
        cv_value = f"{cv:.2f}"
        # Lower CV = more predictable output. Thresholds map to cricket archetypes.
        if cv < 0.40:
            cv_tag = "Dependable"
        elif cv < 0.80:
            cv_tag = "Streaky"
        else:
            cv_tag = "Boom-or-Bust"
    else:
        cv_value = "—"
        cv_tag   = "—"

    # ── Metric cards ─────────────────────────────────────────────────
    # In comparison mode: 4 side-by-side comparison cards replace the standard 5.
    # Cards shown depend on cmp_type: batting stats for batters, bowling for bowlers,
    # a 2+2 split for allrounders / mixed pairs.
    # In single-player mode: normal 5 cards (SR, Balls, Boundary%, Dot%, Consistency).
    def _cmp_card(stat_label, val_a, val_b, higher_is_better=True):
        # "—" means the player has no data for this stat - no winner highlighted
        a_str = str(val_a)
        b_str = str(val_b)
        try:
            a_num = float(a_str.replace("%", ""))
            b_num = float(b_str.replace("%", ""))
            a_win = (a_num > b_num) == higher_is_better
            b_win = (b_num > a_num) == higher_is_better
        except ValueError:
            a_win = b_win = False
        return html.Div([
            html.Span(stat_label, className="metric-card__label"),
            html.Div([
                html.Div([
                    html.Span(name_a, style={"fontSize": "9px", "color": "#888", "fontFamily": "Inter, system-ui, sans-serif"}),
                    html.Div(a_str, className="metric-card__value",
                             style={"color": "#3b82f6" if a_win else "#888"}),
                ], style={"textAlign": "center", "flex": "1"}),
                html.Div("vs", style={"fontSize": "9px", "color": "#ccc", "fontFamily": "Inter, system-ui, sans-serif",
                                      "alignSelf": "center", "padding": "0 8px"}),
                html.Div([
                    html.Span(name_b, style={"fontSize": "9px", "color": "#888", "fontFamily": "Inter, system-ui, sans-serif"}),
                    html.Div(b_str, className="metric-card__value",
                             style={"color": "#f97316" if b_win else "#888"}),
                ], style={"textAlign": "center", "flex": "1"}),
            ], style={"display": "flex", "alignItems": "flex-end", "gap": "0"}),
        ], className="metric-card")

    if player_compare and cmp_type == "bat":
        # Both pure batters: 4 batting cards
        metrics = [
            dbc.Col(_cmp_card("Strike Rate",  sr,         c_sr,       higher_is_better=True),  width=3),
            dbc.Col(_cmp_card("Runs",         total_runs, c_runs,     higher_is_better=True),  width=3),
            dbc.Col(_cmp_card("Boundary %",   f"{bpct}%", f"{c_bpct}%", higher_is_better=True),  width=3),
            dbc.Col(_cmp_card("Dot Ball %",   f"{dpct}%", f"{c_dpct}%", higher_is_better=False), width=3),
        ]
    elif player_compare and cmp_type == "bowl":
        # Both pure bowlers: 4 bowling cards
        av = a_bowl or {}
        bv = b_bowl or {}
        metrics = [
            dbc.Col(_cmp_card("Wickets",      av.get("wickets", "—"),    bv.get("wickets", "—"),    higher_is_better=True),  width=3),
            dbc.Col(_cmp_card("Economy",      av.get("economy", "—"),    bv.get("economy", "—"),    higher_is_better=False), width=3),
            dbc.Col(_cmp_card("Bowl Dot %",   av.get("dot_pct", "—"),    bv.get("dot_pct", "—"),    higher_is_better=True),  width=3),
            dbc.Col(_cmp_card("Balls Bowled", av.get("balls", "—"),      bv.get("balls", "—"),      higher_is_better=True),  width=3),
        ]
    elif player_compare and cmp_type == "mixed":
        # Allrounder or mixed pair: 2 batting + 2 bowling cards.
        # "—" for stats that don't apply to that player.
        av = a_bowl or {}
        bv = b_bowl or {}
        a_bat_sr    = sr         if role_a != "bowler" else "—"
        b_bat_sr    = c_sr       if role_b != "bowler" else "—"
        a_bat_runs  = total_runs if role_a != "bowler" else "—"
        b_bat_runs  = c_runs     if role_b != "bowler" else "—"
        metrics = [
            dbc.Col(_cmp_card("Strike Rate",  a_bat_sr,               b_bat_sr,               higher_is_better=True),  width=3),
            dbc.Col(_cmp_card("Runs",         a_bat_runs,             b_bat_runs,             higher_is_better=True),  width=3),
            dbc.Col(_cmp_card("Wickets",      av.get("wickets", "—"), bv.get("wickets", "—"), higher_is_better=True),  width=3),
            dbc.Col(_cmp_card("Economy",      av.get("economy", "—"), bv.get("economy", "—"), higher_is_better=False), width=3),
        ]
    else:
        metrics = [
            dbc.Col(metric_card("Strike Rate",  str(sr),          secondary=sr_delta,   progress=int(min(sr / 200 * 100, 100)),          color="blue"),   width=3),
            dbc.Col(metric_card("Balls Faced",  str(total_balls),                        progress=int(min(total_balls / 500 * 100, 100)), color="green"),  width=3),
            dbc.Col(metric_card("Boundary %",   f"{bpct}%",       secondary=bpct_delta, progress=int(min(bpct / 40 * 100, 100)),          color="orange"), width=3),
            dbc.Col(metric_card("Dot Ball %",   f"{dpct}%",       secondary=dpct_delta, progress=int(dpct),                               color="red"),    width=3),
        ]

    # ── Phase SR chart ────────────────────────────────────────────────
    # Computed from DEL directly so this responds to the season filter.
    # In comparison mode (player_compare is set), switches to a grouped bar
    # showing player A (blue) vs player B (orange) side by side per phase.

    def _phase_sr(legal_df):
        """Return a dict mapping phase -> strike_rate for one player's legal balls."""
        rows = {}
        for ph in PHASE_ORDER:
            ph_del = legal_df[legal_df["phase"] == ph]
            balls  = len(ph_del)
            if balls > 0:
                rows[ph] = ph_del["batter_runs"].sum() / balls * 100
        return rows

    sr_a = _phase_sr(player_legal)

    fig_phase = go.Figure()

    if player_compare:
        # Comparison mode: grouped horizontal bars, player A = blue, player B = orange
        # compare_legal, name_a, name_b already computed at the top of this callback.
        sr_b = _phase_sr(compare_legal)

        # Only show phases where at least one player has data
        phases_to_show = [ph for ph in PHASE_ORDER if ph in sr_a or ph in sr_b]

        a_vals = [sr_a.get(ph, 0) for ph in phases_to_show]
        b_vals = [sr_b.get(ph, 0) for ph in phases_to_show]

        fig_phase.add_trace(go.Bar(
            name=name_a,
            x=a_vals, y=phases_to_show,
            orientation="h",
            marker_color="#3b82f6",
            marker_line_width=0,
            width=0.35,
            text=[f"{v:.0f}" for v in a_vals],
            textposition="outside",
            textfont={"size": 9, "color": "#888"},
        ))
        fig_phase.add_trace(go.Bar(
            name=name_b,
            x=b_vals, y=phases_to_show,
            orientation="h",
            marker_color="#f97316",
            marker_line_width=0,
            width=0.35,
            text=[f"{v:.0f}" for v in b_vals],
            textposition="outside",
            textfont={"size": 9, "color": "#888"},
        ))

        x_max = max(max(a_vals, default=0), max(b_vals, default=0)) * 1.4

        fig_phase.update_layout(**CHART_THEME)
        fig_phase.update_layout(
            barmode="group",
            showlegend=True,
            legend={"font": {"size": 9, "color": "#888", "family": "Inter, system-ui, sans-serif"},
                    "orientation": "h", "yanchor": "bottom", "y": 1.02, "xanchor": "right", "x": 1},
            yaxis={"categoryorder": "array", "categoryarray": PHASE_ORDER[::-1]},
            margin={**CHART_THEME["margin"], "l": 80, "r": 40},
            xaxis={**CHART_THEME["xaxis"], "range": [0, x_max]},
        )
        phase_label = f"Strike Rate by Phase · {name_a} vs {name_b}"

    else:
        # Single-player mode: colored horizontal bars + league avg tick marks
        phases_with_data = [ph for ph in PHASE_ORDER if ph in sr_a]

        if phases_with_data:
            fig_phase.add_trace(go.Bar(
                x=[sr_a[ph] for ph in phases_with_data],
                y=phases_with_data,
                orientation="h",
                marker_color=[PHASE_COLORS[p] for p in phases_with_data],
                marker_line_width=0,
                width=0.5,
                text=[f"{sr_a[ph]:.0f}" for ph in phases_with_data],
                textposition="outside",
                textfont={"size": 10, "color": "#888"},
                showlegend=False,
            ))

            for phase in phases_with_data:
                if phase in league_avgs:
                    fig_phase.add_trace(go.Scatter(
                        x=[league_avgs[phase]],
                        y=[phase],
                        mode="markers+text",
                        marker=dict(symbol="line-ns-open", size=22, color="#ccc",
                                    line=dict(width=2, color="#ccc")),
                        text=[f"avg {league_avgs[phase]:.0f}"],
                        textposition="bottom center",
                        textfont=dict(size=9, color="#aaa", family="IBM Plex Mono"),
                        showlegend=False,
                        hovertemplate=f"League avg ({phase}): {league_avgs[phase]:.0f}<extra></extra>",
                    ))

        x_max = max(
            max(sr_a.values(), default=0),
            max(league_avgs.values(), default=0),
        ) * 1.35

        fig_phase.update_layout(**CHART_THEME)
        fig_phase.update_layout(
            yaxis={"categoryorder": "array", "categoryarray": PHASE_ORDER[::-1]},
            margin={**CHART_THEME["margin"], "l": 80, "r": 40},
            xaxis={**CHART_THEME["xaxis"], "range": [0, x_max]},
        )
        phase_label = "Strike Rate by Phase  ·  tick = league avg"

    phase_chart = [
        html.Span(phase_label, className="chart-card__label"),
        dcc.Graph(figure=fig_phase, config={"displayModeBar": False}, style={"height": "180px"}),
    ]

    # ── Matchup chart - pre-computed 2021-26, does not change with filter ──
    # matchup_metric controls which column to plot (dismissal_prob / strike_rate / boundary_rate)
    _METRIC_META = {
        "dismissal_prob": {"label": "Dismissal Probability by Bowler · 2021-26", "suffix": "%",  "fmt": ".1f%"},
        "strike_rate":    {"label": "Strike Rate by Bowler · 2021-26",            "suffix": "",   "fmt": ".0f"},
        "boundary_rate":  {"label": "Boundary Rate by Bowler · 2021-26",          "suffix": "%",  "fmt": ".1f%"},
    }
    metric_col  = matchup_metric or "dismissal_prob"
    metric_info = _METRIC_META[metric_col]

    def _build_matchup_fig(data, color):
        """Build a horizontal bar matchup chart for one player's data."""
        fmt      = metric_info["fmt"]
        bar_text = [f"{v:{fmt}}" if "%" not in fmt else f"{v:.1f}%" for v in data[metric_col]]
        fig = go.Figure(go.Bar(
            x=data[metric_col],
            y=data["bowler_name"],
            orientation="h",
            marker_color=color,
            marker_line_width=0,
            width=0.5,
            text=bar_text,
            textposition="outside",
            textfont={"size": 10, "color": "#888"},
        ))
        fig.update_layout(**CHART_THEME)
        x_cfg = {**CHART_THEME["xaxis"]}
        if metric_info["suffix"]:
            x_cfg["ticksuffix"] = metric_info["suffix"]
        # Explicit tickvals forces Plotly to render every name - without this,
        # Plotly auto-skips labels when bars are close together.
        fig.update_layout(
            yaxis={
                "tickmode": "array",
                "tickvals": data["bowler_name"].tolist(),
                "ticktext": data["bowler_name"].tolist(),
                "tickfont": {"family": "Inter, system-ui, sans-serif", "size": 9},
            },
            margin={**CHART_THEME["margin"], "l": 150, "r": 50},
            xaxis=x_cfg,
        )
        return fig

    # In comparison mode, limit to 5 per player to keep the card from growing too tall.
    n_rows = 5 if player_compare else 8
    bm = (
        _matchups[_matchups["batter"] == player]
        .sort_values(metric_col, ascending=False)
        .head(n_rows)
    ).copy()
    if not bm.empty:
        bm["bowler_name"] = bm["bowler"].map(_display_name)

    # In comparison mode (and at least one player bats), stack both players' charts.
    if player_compare and cmp_type != "bowl":
        bm_b = (
            _matchups[_matchups["batter"] == player_compare]
            .sort_values(metric_col, ascending=False)
            .head(5)
        ).copy()
        if not bm_b.empty:
            bm_b["bowler_name"] = bm_b["bowler"].map(_display_name)

        # Player name sub-label style - matches the two-player color coding used everywhere else
        def _player_sublabel(name, color):
            return html.Span(name, style={
                "fontSize": "10px", "color": color, "display": "block",
                "fontFamily": "Inter, system-ui, sans-serif", "marginTop": "8px",
            })

        matchup_parts = [html.Span(metric_info["label"] + " · Comparison", className="chart-card__label")]

        # Player A block
        if not bm.empty:
            ch_a = max(120, len(bm) * 28 + 30)
            matchup_parts += [
                _player_sublabel(_display_name(player), "#3b82f6"),
                dcc.Graph(figure=_build_matchup_fig(bm, "#3b82f6"),
                          config={"displayModeBar": False}, style={"height": f"{ch_a}px"}),
            ]
        else:
            matchup_parts.append(html.P(f"No matchup data for {_display_name(player)}.",
                                        style={"fontSize": "11px", "color": "#888", "marginTop": "8px"}))

        # Player B block - only makes sense if they bat
        if role_b != "bowler":
            if not bm_b.empty:
                ch_b = max(120, len(bm_b) * 28 + 30)
                matchup_parts += [
                    _player_sublabel(_display_name(player_compare), "#f97316"),
                    dcc.Graph(figure=_build_matchup_fig(bm_b, "#f97316"),
                              config={"displayModeBar": False}, style={"height": f"{ch_b}px"}),
                ]
            else:
                matchup_parts.append(html.P(f"No matchup data for {_display_name(player_compare)}.",
                                            style={"fontSize": "11px", "color": "#888", "marginTop": "8px"}))

        matchup_chart = matchup_parts

    elif bm.empty:
        matchup_chart = [
            html.Span("Bowler Matchups · 2021-26", className="chart-card__label"),
            html.P("No matchup data - need 20+ balls vs a single bowler.",
                   style={"fontSize": "11px", "color": "#888", "marginTop": "12px"}),
        ]
    else:
        chart_h = max(180, len(bm) * 30 + 40)
        matchup_chart = [
            html.Span(metric_info["label"], className="chart-card__label"),
            dcc.Graph(figure=_build_matchup_fig(bm, "#3b82f6"),
                      config={"displayModeBar": False}, style={"height": f"{chart_h}px"}),
        ]

    # ── Cluster badge - pre-computed 2021-26, does not change with filter ──
    profile_row = _profiles[_profiles["batter"] == player]
    if not profile_row.empty:
        cluster_id    = int(profile_row.iloc[0]["cluster"])
        label, color  = _CLUSTER_LABELS[cluster_id]
        cluster_badge = html.Span(
            label,
            className="cluster-badge",
            style={"backgroundColor": color + "22", "color": color, "borderColor": color + "55"},
        )
    else:
        cluster_badge = None  # hide the badge row entirely when the player has no cluster data

    # ── Impact CV badge (shown inline next to the player dropdowns) ───
    if cv_value != "—":
        cv_badge = html.Span([
            html.Span("Impact CV ", style={"color": "#888", "fontFamily": "Inter, system-ui, sans-serif", "fontSize": "10px", "fontWeight": "500", "letterSpacing": "0.05em", "textTransform": "uppercase"}),
            html.Span(cv_value, style={"color": "#111", "fontFamily": "IBM Plex Mono, monospace", "fontSize": "13px", "fontWeight": "600"}),
            html.Span(f" · {cv_tag}", style={"color": "#3b82f6", "fontFamily": "IBM Plex Mono, monospace", "fontSize": "11px"}),
        ], style={
            "background": "#f0f6ff",
            "border": "1px solid #bfdbfe",
            "borderRadius": "4px",
            "padding": "6px 12px",
            "display": "inline-flex",
            "alignItems": "baseline",
            "gap": "2px",
        })
    else:
        cv_badge = None

    # ── Impact score trend ────────────────────────────────────────────
    imp = _impact[
        (_impact["player"] == player) &
        (_impact["season"] >= min_yr) &
        (_impact["season"] <= max_yr)
    ].sort_values("season")

    if imp.empty:
        impact_chart = [
            html.Span("Impact Score by Season", className="chart-card__label"),
            html.P("No impact data available.",
                   style={"fontSize": "11px", "color": "#888", "marginTop": "12px"}),
        ]
    elif player_compare:
        # Comparison mode: line traces for both players so trends read side by side
        imp_b = _impact[
            (_impact["player"] == player_compare) &
            (_impact["season"] >= min_yr) &
            (_impact["season"] <= max_yr)
        ].sort_values("season")

        fig_imp = go.Figure()
        fig_imp.add_trace(go.Scatter(
            x=[str(int(s)) for s in imp["season"]], y=imp["avg_impact"],
            name=name_a, mode="lines+markers",
            line={"color": "#3b82f6", "width": 2},
            marker={"size": 6},
            customdata=imp["matches_played"].values,
            hovertemplate=f"{name_a} %{{x}}: <b>%{{y:+.2f}}</b>  (%{{customdata}} matches)<extra></extra>",
        ))
        if not imp_b.empty:
            fig_imp.add_trace(go.Scatter(
                x=[str(int(s)) for s in imp_b["season"]], y=imp_b["avg_impact"],
                name=name_b, mode="lines+markers",
                line={"color": "#f97316", "width": 2},
                marker={"size": 6},
                customdata=imp_b["matches_played"].values,
                hovertemplate=f"{name_b} %{{x}}: <b>%{{y:+.2f}}</b>  (%{{customdata}} matches)<extra></extra>",
            ))
        fig_imp.add_hline(y=0, line_dash="dot", line_color="#e5e5e5", line_width=1)
        # Integer range between earliest and latest season across both players so
        # gap years (e.g. 2023 if one player was injured) still appear on the x-axis.
        imp_int = sorted(set(
            [int(s) for s in imp["season"]] +
            ([int(s) for s in imp_b["season"]] if not imp_b.empty else [])
        ))
        imp_seasons = [str(y) for y in range(imp_int[0], imp_int[-1] + 1)] if imp_int else []
        fig_imp.update_layout(**CHART_THEME)
        fig_imp.update_layout(
            showlegend=True,
            legend={"font": {"size": 9, "color": "#888", "family": "Inter, system-ui, sans-serif"},
                    "orientation": "h", "yanchor": "bottom", "y": 1.02, "xanchor": "right", "x": 1},
            xaxis={**CHART_THEME["xaxis"], "categoryorder": "array", "categoryarray": imp_seasons},
            yaxis={**CHART_THEME["yaxis"], "zeroline": False},
        )
        impact_chart = [
            html.Span("Impact Score Comparison · 0 = league average", className="chart-card__label"),
            dcc.Graph(figure=fig_imp, config={"displayModeBar": False}, style={"height": "180px"}),
        ]
    else:
        bar_colors = ["#3b82f6" if v >= 0 else "#ef4444" for v in imp["avg_impact"]]
        seasons    = [str(int(s)) for s in imp["season"]]

        fig_imp = go.Figure(go.Bar(
            x=seasons,
            y=imp["avg_impact"],
            marker_color=bar_colors,
            marker_line_width=0,
            text=[f"{v:+.2f}" for v in imp["avg_impact"]],
            textposition="outside",
            textfont={"size": 9, "color": "#888", "family": "IBM Plex Mono"},
            customdata=imp["matches_played"].values,
            hovertemplate="%{x}: <b>%{y:+.2f}</b><br>Matches: %{customdata}<extra></extra>",
        ))

        fig_imp.add_hline(y=0, line_dash="dot", line_color="#e5e5e5", line_width=1)

        y_abs   = imp["avg_impact"].abs().max()
        y_range = [-(y_abs * 1.5), y_abs * 1.5]

        fig_imp.update_layout(**CHART_THEME)
        fig_imp.update_layout(
            yaxis={**CHART_THEME["yaxis"], "range": y_range, "zeroline": False},
            xaxis={**CHART_THEME["xaxis"]},
        )

        impact_chart = [
            html.Span("Impact Score by Season · 2021-26  ·  0 = league average", className="chart-card__label"),
            dcc.Graph(figure=fig_imp, config={"displayModeBar": False}, style={"height": "180px"}),
        ]

    # ── Season-by-season batting: runs + SR per season ────────────────
    # For each season in the window, compute the player's runs, balls, SR
    # alongside the league average SR for that season (all qualifiers with 50+ balls).
    season_rows = []
    for szn in sorted(player_legal["season"].unique()):
        szn_del = player_legal[player_legal["season"] == szn]
        balls   = len(szn_del)
        if balls < 5:
            continue
        runs = int(szn_del["batter_runs"].sum())
        sr   = round(runs / balls * 100, 1)

        # League avg SR for this season: all players with 50+ balls
        league_szn = DEL[
            (DEL["season"] == szn) & (~DEL["super_over"].astype(bool)) &
            (~DEL["is_wide"].astype(bool))
        ]
        per_player = league_szn.groupby("batter").size()
        qualified  = per_player[per_player >= 50].index
        if len(qualified) > 0:
            q      = league_szn[league_szn["batter"].isin(qualified)]
            lg_sr  = q["batter_runs"].sum() / len(q) * 100
        else:
            lg_sr  = None
        season_rows.append({"season": str(int(szn)), "runs": runs, "sr": sr, "league_sr": lg_sr})

    df_ssn = pd.DataFrame(season_rows)

    if df_ssn.empty and not player_compare:
        season_chart = [
            html.Span("Season-by-Season Batting", className="chart-card__label"),
            html.P("No batting data in this window.",
                   style={"fontSize": "11px", "color": "#888", "marginTop": "12px"}),
        ]
    elif player_compare and cmp_type == "bowl":
        # Both pure bowlers: show economy per season for both
        def _bowl_season_econ(legal_df, all_df):
            rows = []
            for szn in sorted(legal_df["season"].unique()):
                szn_legal = legal_df[legal_df["season"] == szn]
                szn_all   = all_df[all_df["season"] == szn]
                b = len(szn_legal)
                if b < 6:
                    continue
                rows.append({"season": str(int(szn)), "econ": round(szn_all["total_runs"].sum() / (b / 6), 2)})
            return pd.DataFrame(rows)

        a_bowl_all   = DEL[(DEL["bowler"] == player)         & (DEL["season"] >= min_yr) & (DEL["season"] <= max_yr) & (~DEL["super_over"].astype(bool))]
        b_bowl_all   = DEL[(DEL["bowler"] == player_compare) & (DEL["season"] >= min_yr) & (DEL["season"] <= max_yr) & (~DEL["super_over"].astype(bool))]
        a_bowl_legal = a_bowl_all[~a_bowl_all["is_wide"].astype(bool)]
        b_bowl_legal = b_bowl_all[~b_bowl_all["is_wide"].astype(bool)]
        df_a_econ    = _bowl_season_econ(a_bowl_legal, a_bowl_all)
        df_b_econ    = _bowl_season_econ(b_bowl_legal, b_bowl_all)

        fig_ssn = go.Figure()
        if not df_a_econ.empty:
            fig_ssn.add_trace(go.Scatter(
                x=df_a_econ["season"], y=df_a_econ["econ"],
                name=name_a, mode="lines+markers",
                line={"color": "#3b82f6", "width": 2}, marker={"size": 6},
                hovertemplate=f"{name_a} %{{x}}: Economy <b>%{{y:.2f}}</b><extra></extra>",
            ))
        if not df_b_econ.empty:
            fig_ssn.add_trace(go.Scatter(
                x=df_b_econ["season"], y=df_b_econ["econ"],
                name=name_b, mode="lines+markers",
                line={"color": "#f97316", "width": 2}, marker={"size": 6},
                hovertemplate=f"{name_b} %{{x}}: Economy <b>%{{y:.2f}}</b><extra></extra>",
            ))
        bowl_int = sorted(set(
            ([int(s) for s in df_a_econ["season"]] if not df_a_econ.empty else []) +
            ([int(s) for s in df_b_econ["season"]] if not df_b_econ.empty else [])
        ))
        bowl_seasons = [str(y) for y in range(bowl_int[0], bowl_int[-1] + 1)] if bowl_int else []
        fig_ssn.update_layout(**CHART_THEME)
        fig_ssn.update_layout(
            showlegend=True,
            legend={"font": {"size": 9, "color": "#888", "family": "Inter, system-ui, sans-serif"},
                    "orientation": "h", "yanchor": "bottom", "y": 1.02, "xanchor": "right", "x": 1},
            yaxis={**CHART_THEME["yaxis"], "title": {"text": "Economy", "font": {"size": 9, "color": "#777"}}},
            xaxis={**CHART_THEME["xaxis"], "categoryorder": "array", "categoryarray": bowl_seasons},
        )
        season_chart = [
            html.Span("Economy by Season Comparison", className="chart-card__label"),
            dcc.Graph(figure=fig_ssn, config={"displayModeBar": False}, style={"height": "180px"}),
        ]
    elif player_compare and cmp_type in ("bat", "mixed"):
        # Two pure batters: stack the full runs+SR chart for each player.
        def _build_bat_szn_fig(legal_df, include_lg_avg=True):
            rows = []
            for szn in sorted(legal_df["season"].unique()):
                szn_del = legal_df[legal_df["season"] == szn]
                b = len(szn_del)
                if b < 5:
                    continue
                runs = int(szn_del["batter_runs"].sum())
                sr   = round(runs / b * 100, 1)
                lg_sr = None
                if include_lg_avg:
                    lg_szn = DEL[(DEL["season"] == szn) & (~DEL["super_over"].astype(bool)) & (~DEL["is_wide"].astype(bool))]
                    per_p  = lg_szn.groupby("batter").size()
                    q      = per_p[per_p >= 50].index
                    if len(q) > 0:
                        qd    = lg_szn[lg_szn["batter"].isin(q)]
                        lg_sr = qd["batter_runs"].sum() / len(qd) * 100
                rows.append({"season": str(int(szn)), "runs": runs, "sr": sr, "league_sr": lg_sr})
            if not rows:
                return None
            df = pd.DataFrame(rows)
            ssn_int   = [int(s) for s in df["season"]]
            ssn_range = [str(y) for y in range(min(ssn_int), max(ssn_int) + 1)]
            fig = go.Figure()
            fig.add_trace(go.Bar(
                x=df["season"], y=df["runs"], name="Runs",
                marker_color="#3b82f6", marker_line_width=0,
                text=df["runs"].astype(str), textposition="outside",
                textfont={"size": 9, "color": "#777", "family": "IBM Plex Mono, monospace"},
                hovertemplate="%{x}: <b>%{y} runs</b><extra></extra>",
            ))
            fig.add_trace(go.Scatter(
                x=df["season"], y=df["sr"], name="SR",
                mode="lines+markers", line={"color": "#f97316", "width": 1.5},
                marker={"size": 5}, yaxis="y2",
                hovertemplate="%{x}: SR <b>%{y:.0f}</b><extra></extra>",
            ))
            if include_lg_avg:
                lg_notna = df[df["league_sr"].notna()]
                if not lg_notna.empty:
                    fig.add_trace(go.Scatter(
                        x=lg_notna["season"], y=lg_notna["league_sr"],
                        name="League avg SR", mode="lines",
                        line={"color": "#e5e5e5", "width": 1, "dash": "dot"},
                        yaxis="y2",
                        hovertemplate="League avg SR: <b>%{y:.0f}</b><extra></extra>",
                    ))
            fig.update_layout(**CHART_THEME)
            fig.update_layout(
                showlegend=True,
                legend={"font": {"size": 9, "color": "#888", "family": "Inter, system-ui, sans-serif"},
                        "orientation": "h", "yanchor": "bottom", "y": 1.02, "xanchor": "right", "x": 1},
                yaxis={**CHART_THEME["yaxis"], "title": {"text": "Runs", "font": {"size": 9, "color": "#777"}}},
                yaxis2={"overlaying": "y", "side": "right", "showgrid": False, "showline": False,
                        "tickfont": {"family": "IBM Plex Mono, monospace", "size": 9, "color": "#f97316"},
                        "title": {"text": "SR", "font": {"size": 9, "color": "#f97316"}}},
                xaxis={**CHART_THEME["xaxis"], "categoryorder": "array", "categoryarray": ssn_range},
                margin={**CHART_THEME["margin"], "r": 40},
            )
            return fig

        def _player_sublabel(name, color):
            return html.Span(name, style={
                "fontSize": "10px", "color": color, "display": "block",
                "fontFamily": "Inter, system-ui, sans-serif", "marginTop": "8px",
            })

        fig_a = _build_bat_szn_fig(player_legal, include_lg_avg=True)
        fig_b = _build_bat_szn_fig(compare_legal, include_lg_avg=False) if c_balls > 0 else None
        season_chart = [
            html.Span("Season-by-Season · Bars = Runs  ·  Line = SR vs League Avg", className="chart-card__label"),
            _player_sublabel(_display_name(player), "#3b82f6"),
            (dcc.Graph(figure=fig_a, config={"displayModeBar": False}, style={"height": "180px"})
             if fig_a else html.P("No data.", style={"fontSize": "11px", "color": "#888"})),
            _player_sublabel(_display_name(player_compare), "#f97316"),
            (dcc.Graph(figure=fig_b, config={"displayModeBar": False}, style={"height": "180px"})
             if fig_b else html.P("No data.", style={"fontSize": "11px", "color": "#888"})),
        ]
    elif player_compare:
        # Mixed pair: overlay SR lines so the comparison is direct on a single axis.
        fig_ssn = go.Figure()
        if not df_ssn.empty:
            fig_ssn.add_trace(go.Scatter(
                x=df_ssn["season"], y=df_ssn["sr"],
                name=name_a, mode="lines+markers",
                line={"color": "#3b82f6", "width": 2}, marker={"size": 6},
                hovertemplate=f"{name_a} %{{x}}: SR <b>%{{y:.0f}}</b><extra></extra>",
            ))
        cmp_season_rows = []
        for szn in sorted(compare_legal["season"].unique() if c_balls > 0 else []):
            szn_del = compare_legal[compare_legal["season"] == szn]
            b = len(szn_del)
            if b < 5:
                continue
            cmp_season_rows.append({"season": str(int(szn)), "sr": round(szn_del["batter_runs"].sum() / b * 100, 1)})
        df_cmp = pd.DataFrame(cmp_season_rows)
        if not df_cmp.empty:
            fig_ssn.add_trace(go.Scatter(
                x=df_cmp["season"], y=df_cmp["sr"],
                name=name_b, mode="lines+markers",
                line={"color": "#f97316", "width": 2}, marker={"size": 6},
                hovertemplate=f"{name_b} %{{x}}: SR <b>%{{y:.0f}}</b><extra></extra>",
            ))
        sr_int = sorted(set(
            ([int(s) for s in df_ssn["season"]] if not df_ssn.empty else []) +
            ([int(s) for s in df_cmp["season"]] if not df_cmp.empty else [])
        ))
        sr_seasons = [str(y) for y in range(sr_int[0], sr_int[-1] + 1)] if sr_int else []
        fig_ssn.update_layout(**CHART_THEME)
        fig_ssn.update_layout(
            showlegend=True,
            legend={"font": {"size": 9, "color": "#888", "family": "Inter, system-ui, sans-serif"},
                    "orientation": "h", "yanchor": "bottom", "y": 1.02, "xanchor": "right", "x": 1},
            yaxis={**CHART_THEME["yaxis"], "title": {"text": "Strike Rate", "font": {"size": 9, "color": "#777"}}},
            xaxis={**CHART_THEME["xaxis"], "categoryorder": "array", "categoryarray": sr_seasons},
        )
        season_chart = [
            html.Span("Strike Rate by Season", className="chart-card__label"),
            dcc.Graph(figure=fig_ssn, config={"displayModeBar": False}, style={"height": "180px"}),
        ]
    else:
        fig_ssn = go.Figure()
        fig_ssn.add_trace(go.Bar(
            x=df_ssn["season"], y=df_ssn["runs"],
            name="Runs",
            marker_color="#3b82f6",
            marker_line_width=0,
            text=df_ssn["runs"].astype(str),
            textposition="outside",
            textfont={"size": 9, "color": "#777", "family": "IBM Plex Mono, monospace"},
            hovertemplate="%{x}: <b>%{y} runs</b><extra></extra>",
        ))
        fig_ssn.add_trace(go.Scatter(
            x=df_ssn["season"], y=df_ssn["sr"],
            name="SR",
            mode="lines+markers",
            line={"color": "#f97316", "width": 1.5},
            marker={"size": 5},
            yaxis="y2",
            hovertemplate="%{x}: SR <b>%{y:.0f}</b><extra></extra>",
        ))
        league_line = df_ssn["league_sr"].dropna()
        if not league_line.empty:
            fig_ssn.add_trace(go.Scatter(
                x=df_ssn.loc[df_ssn["league_sr"].notna(), "season"],
                y=league_line,
                name="League avg SR",
                mode="lines",
                line={"color": "#e5e5e5", "width": 1, "dash": "dot"},
                yaxis="y2",
                hovertemplate="League avg SR: <b>%{y:.0f}</b><extra></extra>",
            ))

        # Fill in gap years (e.g. a player who missed 2023) so the axis doesn't jump.
        ssn_int = [int(s) for s in df_ssn["season"]]
        ssn_range = [str(y) for y in range(min(ssn_int), max(ssn_int) + 1)] if ssn_int else []
        fig_ssn.update_layout(**CHART_THEME)
        fig_ssn.update_layout(
            showlegend=True,
            legend={"font": {"size": 9, "color": "#888", "family": "Inter, system-ui, sans-serif"},
                    "orientation": "h", "yanchor": "bottom", "y": 1.02, "xanchor": "right", "x": 1},
            yaxis={**CHART_THEME["yaxis"], "title": {"text": "Runs", "font": {"size": 9, "color": "#777"}}},
            yaxis2={"overlaying": "y", "side": "right", "showgrid": False, "showline": False,
                    "tickfont": {"family": "IBM Plex Mono, monospace", "size": 9, "color": "#f97316"},
                    "title": {"text": "SR", "font": {"size": 9, "color": "#f97316"}}},
            xaxis={**CHART_THEME["xaxis"], "categoryorder": "array", "categoryarray": ssn_range},
            margin={**CHART_THEME["margin"], "r": 40},
        )
        season_chart = [
            html.Span("Season-by-Season · Bars = Runs  ·  Line = SR vs League Avg", className="chart-card__label"),
            dcc.Graph(figure=fig_ssn, config={"displayModeBar": False}, style={"height": "180px"}),
        ]

    # ── Comparison stats row (second row of compare cards) ───────────
    # Row 1 has the 4 main stats. Row 2 shows volume/secondary stats.
    if player_compare and cmp_type == "bat":
        # Volume stats for batter vs batter
        compare_stats = [
            dbc.Col(_cmp_card("Balls Faced", total_balls, c_balls, higher_is_better=True),  width=3),
            dbc.Col(_cmp_card("Fours (4s)",  total_4s,    c_4s,    higher_is_better=True),  width=3),
            dbc.Col(_cmp_card("Sixes (6s)",  total_6s,    c_6s,    higher_is_better=True),  width=3),
            dbc.Col(_cmp_card("Dot Ball %",  f"{dpct}%",  f"{c_dpct}%", higher_is_better=False), width=3),
        ]
    elif player_compare and cmp_type == "bowl":
        # Row 1 already has all 4 bowling stats - nothing extra needed
        compare_stats = []
    elif player_compare and cmp_type == "mixed":
        # Show volume stats for whichever discipline applies
        av = a_bowl or {}
        bv = b_bowl or {}
        a_bf   = total_balls          if role_a != "bowler" else "—"
        b_bf   = c_balls              if role_b != "bowler" else "—"
        compare_stats = [
            dbc.Col(_cmp_card("Balls Faced",  a_bf,                    b_bf,                    higher_is_better=True),  width=3),
            dbc.Col(_cmp_card("Boundary %",   f"{bpct}%" if role_a != "bowler" else "—",
                                              f"{c_bpct}%" if role_b != "bowler" else "—",      higher_is_better=True),  width=3),
            dbc.Col(_cmp_card("Balls Bowled", av.get("balls", "—"),    bv.get("balls", "—"),    higher_is_better=True),  width=3),
            dbc.Col(_cmp_card("Bowl Dot %",   av.get("dot_pct", "—"),  bv.get("dot_pct", "—"),  higher_is_better=True),  width=3),
        ]
    else:
        compare_stats = []

    # ── Bowling section ───────────────────────────────────────────────
    # All deliveries where this player bowled (wides included for run totals)
    bowler_all = DEL[
        (DEL["bowler"]     == player) &
        (DEL["season"]     >= min_yr) &
        (DEL["season"]     <= max_yr) &
        (~DEL["super_over"].astype(bool))
    ]
    # Legal balls only (wides excluded) for ball count and dot ball %
    bowler_legal      = bowler_all[~bowler_all["is_wide"].astype(bool)]
    total_balls_bowled = len(bowler_legal)

    if total_balls_bowled < 50:
        bowl_section = []
    else:
        # Wicket types that count as the bowler's wicket in cricket
        BOWLER_WKT_KINDS = {"caught", "bowled", "lbw", "caught and bowled", "stumped", "hit wicket"}
        wkt_balls     = bowler_legal[bowler_legal["wicket"].astype(bool)]
        total_wickets = int(wkt_balls[wkt_balls["wicket_kind"].isin(BOWLER_WKT_KINDS)].shape[0])

        bowl_dots    = int(bowler_legal["is_dot"].astype(bool).sum())
        bowl_dot_pct = round(bowl_dots / total_balls_bowled * 100, 1)

        total_runs_conceded = int(bowler_all["total_runs"].sum())
        overall_econ        = round(total_runs_conceded / (total_balls_bowled / 6), 2)

        # cmp_bowl_active: True when the compare player also has 50+ legal balls bowled.
        # b_bowl was computed earlier in the callback; "balls" is their legal ball count.
        cmp_bowl_active = (
            player_compare is not None and
            b_bowl is not None and
            b_bowl.get("balls", 0) >= 50
        )
        cb_all = cb_legal = None
        if cmp_bowl_active:
            cb_all   = DEL[(DEL["bowler"] == player_compare) & (DEL["season"] >= min_yr) &
                           (DEL["season"] <= max_yr) & (~DEL["super_over"].astype(bool))]
            cb_legal = cb_all[~cb_all["is_wide"].astype(bool)]

        # ── Economy by phase ─────────────────────────────────────────
        league_avgs_bowl = _LEAGUE_AVG_ECON_RECENT if min_yr >= 2021 else _LEAGUE_AVG_ECON_ALLTIME

        def _phase_econ_df(b_all, b_legal):
            """Economy per phase for one bowler, returned as a DataFrame indexed by phase."""
            rows = []
            for ph in PHASE_ORDER:
                ph_legal = b_legal[b_legal["phase"] == ph]
                ph_all   = b_all[b_all["phase"] == ph]
                balls    = len(ph_legal)
                if balls >= 6:
                    rows.append({
                        "phase":   ph,
                        "economy": ph_all["total_runs"].sum() / (balls / 6),
                        "balls":   balls,
                    })
            return (
                pd.DataFrame(rows).set_index("phase").reindex(PHASE_ORDER).dropna()
                if rows else pd.DataFrame()
            )

        df_econ   = _phase_econ_df(bowler_all, bowler_legal)
        df_econ_b = _phase_econ_df(cb_all, cb_legal) if cmp_bowl_active else pd.DataFrame()

        fig_econ = go.Figure()

        if cmp_bowl_active:
            # Grouped horizontal bars: player A = blue, player B = orange
            all_phases = [ph for ph in PHASE_ORDER if ph in df_econ.index or ph in df_econ_b.index]
            a_vals     = [df_econ.loc[ph, "economy"]   if ph in df_econ.index   else 0 for ph in all_phases]
            b_vals     = [df_econ_b.loc[ph, "economy"] if ph in df_econ_b.index else 0 for ph in all_phases]
            fig_econ.add_trace(go.Bar(
                name=name_a, x=a_vals, y=all_phases, orientation="h",
                marker_color="#3b82f6", marker_line_width=0, width=0.35,
                text=[f"{v:.2f}" for v in a_vals], textposition="outside",
                textfont={"size": 9, "color": "#888"},
            ))
            fig_econ.add_trace(go.Bar(
                name=name_b, x=b_vals, y=all_phases, orientation="h",
                marker_color="#f97316", marker_line_width=0, width=0.35,
                text=[f"{v:.2f}" for v in b_vals], textposition="outside",
                textfont={"size": 9, "color": "#888"},
            ))
            x_max_econ = max(max(a_vals + b_vals, default=12), max(league_avgs_bowl.values(), default=0)) * 1.35
            fig_econ.update_layout(**CHART_THEME)
            fig_econ.update_layout(
                barmode="group",
                showlegend=True,
                legend={"font": {"size": 9, "color": "#888", "family": "Inter, system-ui, sans-serif"},
                        "orientation": "h", "yanchor": "bottom", "y": 1.02, "xanchor": "right", "x": 1},
                yaxis={"categoryorder": "array", "categoryarray": PHASE_ORDER[::-1]},
                margin={**CHART_THEME["margin"], "l": 80, "r": 40},
                xaxis={**CHART_THEME["xaxis"], "range": [0, x_max_econ]},
            )
            econ_label = "Economy by Phase · Comparison"
        else:
            if not df_econ.empty:
                fig_econ.add_trace(go.Bar(
                    x=df_econ["economy"],
                    y=df_econ.index,
                    orientation="h",
                    marker_color=[PHASE_COLORS[p] for p in df_econ.index],
                    marker_line_width=0,
                    width=0.5,
                    text=[f"{v:.2f}" for v in df_econ["economy"]],
                    textposition="outside",
                    textfont={"size": 10, "color": "#888"},
                    showlegend=False,
                ))
                for ph in df_econ.index:
                    if ph in league_avgs_bowl:
                        avg = league_avgs_bowl[ph]
                        fig_econ.add_trace(go.Scatter(
                            x=[avg], y=[ph],
                            mode="markers+text",
                            marker=dict(symbol="line-ns-open", size=22, color="#ccc",
                                        line=dict(width=2, color="#ccc")),
                            text=[f"avg {avg:.1f}"],
                            textposition="bottom center",
                            textfont=dict(size=9, color="#aaa", family="IBM Plex Mono"),
                            showlegend=False,
                            hovertemplate=f"League avg ({ph}): {avg:.2f}<extra></extra>",
                        ))
            x_max_econ = max(
                df_econ["economy"].max() if not df_econ.empty else 12,
                max(league_avgs_bowl.values(), default=0),
            ) * 1.35
            fig_econ.update_layout(**CHART_THEME)
            fig_econ.update_layout(
                yaxis={"categoryorder": "array", "categoryarray": PHASE_ORDER[::-1]},
                margin={**CHART_THEME["margin"], "l": 80, "r": 40},
                xaxis={**CHART_THEME["xaxis"], "range": [0, x_max_econ]},
            )
            econ_label = "Economy by Phase  ·  tick = league avg"

        # ── Wicket type breakdown ─────────────────────────────────────
        WKT_BUCKET_MAP = {
            "caught":           "caught",
            "caught and bowled": "caught",
            "bowled":           "bowled",
            "lbw":              "lbw",
            "stumped":          "stumped",
            "hit wicket":       "other",
        }
        WKT_COLORS = {
            "caught":  "#3b82f6",
            "bowled":  "#22c55e",
            "lbw":     "#f97316",
            "stumped": "#8b5cf6",
            "other":   "#888888",
        }

        def _wkt_buckets(wkt_b):
            b = {"caught": 0, "bowled": 0, "lbw": 0, "stumped": 0, "other": 0}
            for kind in wkt_b["wicket_kind"]:
                bucket = WKT_BUCKET_MAP.get(kind)
                if bucket:
                    b[bucket] += 1
            return b

        buckets = _wkt_buckets(wkt_balls)

        fig_wkt = go.Figure()
        if cmp_bowl_active:
            cb_wkt_b  = cb_legal[cb_legal["wicket"].astype(bool)]
            buckets_b = _wkt_buckets(cb_wkt_b)
            y_labels  = [_display_name(player), _display_name(player_compare)]
            for bucket in ["caught", "bowled", "lbw", "stumped", "other"]:
                a_c = buckets[bucket]
                b_c = buckets_b[bucket]
                if a_c == 0 and b_c == 0:
                    continue
                fig_wkt.add_trace(go.Bar(
                    x=[a_c, b_c], y=y_labels, orientation="h",
                    name=bucket, marker_color=WKT_COLORS[bucket], marker_line_width=0,
                    text=[f"{bucket}  {v}" if v > 0 else "" for v in [a_c, b_c]],
                    textposition="inside", textfont={"size": 9, "color": "white"},
                    hovertemplate=f"{bucket}: %{{x}}<extra></extra>",
                ))
            wkt_h = 120
        else:
            for bucket in ["caught", "bowled", "lbw", "stumped", "other"]:
                count = buckets[bucket]
                if count == 0:
                    continue
                fig_wkt.add_trace(go.Bar(
                    x=[count], y=["Wickets"], orientation="h",
                    name=bucket, marker_color=WKT_COLORS[bucket], marker_line_width=0,
                    text=[f"{bucket}  {count}"], textposition="inside",
                    textfont={"size": 9, "color": "white"},
                    hovertemplate=f"{bucket}: {count}<extra></extra>",
                ))
            wkt_h = 80

        fig_wkt.update_layout(**CHART_THEME)
        fig_wkt.update_layout(
            barmode="stack",
            showlegend=False,
            yaxis={"visible": cmp_bowl_active,
                   "tickfont": {"family": "Inter, system-ui, sans-serif", "size": 9}},
            margin={**CHART_THEME["margin"], "t": 8, "b": 8},
        )

        # ── Danger matchups (bowler's view - batters with highest SR) ─
        def _danger_fig(bowler_name, color):
            """Build danger matchup chart for one bowler. Returns (fig, df) or (None, empty df)."""
            d = (
                _matchups[_matchups["bowler"] == bowler_name]
                .sort_values("strike_rate", ascending=False)
                .head(5)
            ).copy()
            if d.empty:
                return None, d
            d["batter_name"] = d["batter"].map(_display_name)
            # Axis starts at 100 - no meaningful matchup SR will be below this
            sr_max = max(int(d["strike_rate"].max() * 1.2), 120)
            fig = go.Figure(go.Bar(
                x=d["strike_rate"], y=d["batter_name"], orientation="h",
                marker_color=color, marker_line_width=0, width=0.5,
                text=[f"{v:.0f}" for v in d["strike_rate"]],
                textposition="outside", textfont={"size": 10, "color": "#888"},
                customdata=d["balls_faced"].values,
                hovertemplate="SR: %{x:.0f}  ·  Balls: %{customdata}<extra></extra>",
            ))
            fig.update_layout(**CHART_THEME)
            fig.update_layout(
                yaxis={
                    "autorange": "reversed",
                    "tickmode": "array",
                    "tickvals": d["batter_name"].tolist(),
                    "ticktext": d["batter_name"].tolist(),
                    "tickfont": {"family": "Inter, system-ui, sans-serif", "size": 9},
                },
                margin={**CHART_THEME["margin"], "l": 120, "r": 50},
                xaxis={**CHART_THEME["xaxis"], "range": [100, sr_max]},
            )
            return fig, d

        fig_danger_a, _ = _danger_fig(player, "#ef4444")

        def _bowl_sublabel(name, color):
            return html.Span(name, style={
                "fontSize": "10px", "color": color, "display": "block",
                "fontFamily": "Inter, system-ui, sans-serif", "marginTop": "8px",
            })

        if cmp_bowl_active:
            fig_danger_b, _ = _danger_fig(player_compare, "#ef4444")
            danger_chart_content = html.Div([
                _bowl_sublabel(_display_name(player), "#3b82f6"),
                (dcc.Graph(figure=fig_danger_a, config={"displayModeBar": False}, style={"height": "150px"})
                 if fig_danger_a else html.P("No matchup data.", style={"fontSize": "11px", "color": "#888"})),
                _bowl_sublabel(_display_name(player_compare), "#f97316"),
                (dcc.Graph(figure=fig_danger_b, config={"displayModeBar": False}, style={"height": "150px"})
                 if fig_danger_b else html.P("No matchup data.", style={"fontSize": "11px", "color": "#888"})),
            ])
        elif fig_danger_a:
            danger_chart_content = dcc.Graph(
                figure=fig_danger_a, config={"displayModeBar": False}, style={"height": "180px"}
            )
        else:
            danger_chart_content = html.P(
                "No matchup data - need 20+ balls vs a single batter.",
                style={"fontSize": "11px", "color": "#888", "marginTop": "12px"},
            )

        # ── Bowling season-by-season: wickets + economy per season ──────
        def _build_bowl_szn_fig(b_all, b_legal, include_lg_avg=True):
            """Build wickets-bar + economy-line season chart for one bowler."""
            rows = []
            for szn in sorted(b_legal["season"].unique()):
                szn_l = b_legal[b_legal["season"] == szn]
                szn_a = b_all[b_all["season"] == szn]
                b = len(szn_l)
                if b < 6:
                    continue
                wkts = int(szn_l[szn_l["wicket_kind"].isin(BOWLER_WKT_KINDS)].shape[0])
                econ = round(szn_a["total_runs"].sum() / (b / 6), 2)
                lg_econ = None
                if include_lg_avg:
                    lg_szn_all   = DEL[(DEL["season"] == szn) & (~DEL["super_over"].astype(bool))]
                    lg_szn_legal = lg_szn_all[~lg_szn_all["is_wide"].astype(bool)]
                    per_b = lg_szn_legal.groupby("bowler").size()
                    q_b   = per_b[per_b >= 50].index
                    if len(q_b) > 0:
                        lg_runs  = lg_szn_all[lg_szn_all["bowler"].isin(q_b)]["total_runs"].sum()
                        lg_balls = len(lg_szn_legal[lg_szn_legal["bowler"].isin(q_b)])
                        lg_econ  = round(lg_runs / (lg_balls / 6), 2) if lg_balls > 0 else None
                rows.append({"season": str(int(szn)), "wickets": wkts, "economy": econ, "league_econ": lg_econ})

            if not rows:
                return None

            df = pd.DataFrame(rows)
            szn_int = [int(s) for s in df["season"]]
            szn_range = [str(y) for y in range(min(szn_int), max(szn_int) + 1)]

            fig = go.Figure()
            fig.add_trace(go.Bar(
                x=df["season"], y=df["wickets"], name="Wickets",
                marker_color="#3b82f6", marker_line_width=0,
                text=df["wickets"].astype(str), textposition="outside",
                textfont={"size": 9, "color": "#777", "family": "IBM Plex Mono, monospace"},
                hovertemplate="%{x}: <b>%{y} wickets</b><extra></extra>",
            ))
            fig.add_trace(go.Scatter(
                x=df["season"], y=df["economy"], name="Economy",
                mode="lines+markers", line={"color": "#f97316", "width": 1.5},
                marker={"size": 5}, yaxis="y2",
                hovertemplate="%{x}: Economy <b>%{y:.2f}</b><extra></extra>",
            ))
            if include_lg_avg:
                lg_notna = df[df["league_econ"].notna()]
                if not lg_notna.empty:
                    fig.add_trace(go.Scatter(
                        x=lg_notna["season"], y=lg_notna["league_econ"],
                        name="League avg econ", mode="lines",
                        line={"color": "#888", "width": 1, "dash": "dot"},
                        yaxis="y2",
                        hovertemplate="League avg econ: <b>%{y:.2f}</b><extra></extra>",
                    ))
            fig.update_layout(**CHART_THEME)
            fig.update_layout(
                showlegend=True,
                legend={"font": {"size": 9, "color": "#888", "family": "Inter, system-ui, sans-serif"},
                        "orientation": "h", "yanchor": "bottom", "y": 1.02, "xanchor": "right", "x": 1},
                yaxis={**CHART_THEME["yaxis"], "title": {"text": "Wickets", "font": {"size": 9, "color": "#777"}}},
                yaxis2={"overlaying": "y", "side": "right", "showgrid": False, "showline": False,
                        "tickfont": {"family": "IBM Plex Mono, monospace", "size": 9, "color": "#f97316"},
                        "title": {"text": "Economy", "font": {"size": 9, "color": "#f97316"}}},
                xaxis={**CHART_THEME["xaxis"], "categoryorder": "array", "categoryarray": szn_range},
                margin={**CHART_THEME["margin"], "r": 40},
            )
            return fig

        fig_bowl_szn_a = _build_bowl_szn_fig(bowler_all, bowler_legal, include_lg_avg=True)

        if cmp_bowl_active:
            # Compare player's chart: no league avg line (the primary chart already has it)
            fig_bowl_szn_b = _build_bowl_szn_fig(cb_all, cb_legal, include_lg_avg=False)
            bowl_season_content = html.Div([
                _bowl_sublabel(_display_name(player), "#3b82f6"),
                (dcc.Graph(figure=fig_bowl_szn_a, config={"displayModeBar": False}, style={"height": "180px"})
                 if fig_bowl_szn_a else html.P("No season data.", style={"fontSize": "11px", "color": "#888"})),
                _bowl_sublabel(_display_name(player_compare), "#f97316"),
                (dcc.Graph(figure=fig_bowl_szn_b, config={"displayModeBar": False}, style={"height": "180px"})
                 if fig_bowl_szn_b else html.P("No season data.", style={"fontSize": "11px", "color": "#888"})),
            ])
        elif fig_bowl_szn_a:
            bowl_season_content = dcc.Graph(
                figure=fig_bowl_szn_a, config={"displayModeBar": False}, style={"height": "180px"}
            )
        else:
            bowl_season_content = html.P(
                "No season data available.",
                style={"fontSize": "11px", "color": "#888", "marginTop": "12px"},
            )

        # ── Assemble the full bowling section ─────────────────────────
        # In comparison mode, metric cards switch to side-by-side comparison cards.
        if cmp_bowl_active:
            bowl_metrics = dbc.Row([
                dbc.Col(_cmp_card("Wickets",      total_wickets,       b_bowl.get("wickets", "—"), higher_is_better=True),  width=3),
                dbc.Col(_cmp_card("Economy",      overall_econ,        b_bowl.get("economy", "—"), higher_is_better=False), width=3),
                dbc.Col(_cmp_card("Bowl Dot %",   f"{bowl_dot_pct}%",  b_bowl.get("dot_pct", "—"), higher_is_better=True),  width=3),
                dbc.Col(_cmp_card("Balls Bowled", total_balls_bowled,  b_bowl.get("balls", "—"),   higher_is_better=True),  width=3),
            ], className="card-row")
        else:
            bowl_metrics = dbc.Row([
                dbc.Col(metric_card("Wickets",      str(total_wickets),
                                    progress=int(min(total_wickets / 50 * 100, 100)), color="blue"),  width=3),
                dbc.Col(metric_card("Economy",      str(overall_econ),
                                    progress=int(min(max(0, (12 - overall_econ) / 8 * 100), 100)),   color="green"), width=3),
                dbc.Col(metric_card("Bowl Dot %",   f"{bowl_dot_pct}%",
                                    progress=int(bowl_dot_pct),                                       color="orange"), width=3),
                dbc.Col(metric_card("Balls Bowled", str(total_balls_bowled),
                                    progress=int(min(total_balls_bowled / 500 * 100, 100)),           color="red"),  width=3),
            ], className="card-row")

        bowl_section = [
            html.Hr(className="section-divider"),
            html.Span("Bowling", className="section-label"),

            bowl_metrics,

            dbc.Row([
                dbc.Col(html.Div([
                    html.Span(econ_label, className="chart-card__label"),
                    dcc.Graph(figure=fig_econ, config={"displayModeBar": False}, style={"height": "180px"}),
                ], className="chart-card"), width=6),
                dbc.Col(html.Div([
                    html.Span("Wicket Type Breakdown", className="chart-card__label"),
                    dcc.Graph(figure=fig_wkt, config={"displayModeBar": False}, style={"height": f"{wkt_h}px"}),
                ], className="chart-card"), width=6),
            ], className="card-row"),

            dbc.Row([
                dbc.Col(html.Div([
                    html.Span(
                        "Danger Matchups · batters with highest SR vs this bowler · 2021-26",
                        className="chart-card__label",
                    ),
                    danger_chart_content,
                ], className="chart-card"), width=6),
                dbc.Col(html.Div([
                    html.Span(
                        "Season-by-Season · Bars = Wickets  ·  Line = Economy vs League Avg",
                        className="chart-card__label",
                    ),
                    bowl_season_content,
                ], className="chart-card"), width=6),
            ], className="card-row"),
        ]

    return (
        title, metrics, phase_chart, matchup_chart, cluster_badge, cv_badge,
        impact_chart, season_chart, compare_stats, bowl_section,
    )
