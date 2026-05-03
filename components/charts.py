import plotly.graph_objects as go

from components.theme import COLORS


# Applied to every figure via fig.update_layout(**CHART_THEME).
# Rule: always call update_layout(**CHART_THEME) first, then call it again
# to override specific keys. Never spread **CHART_THEME and pass a key it
# already contains in the same call — Python raises "multiple values" error.
_MONO = "IBM Plex Mono, monospace"
_SANS = "Inter, system-ui, sans-serif"

CHART_THEME = {
    "paper_bgcolor": "white",
    "plot_bgcolor":  "white",
    # Default font for all chart text — IBM Plex Mono because chart content is data
    "font": {"family": _MONO, "size": 10, "color": "#aaa"},
    "xaxis": {
        "showgrid":  False,
        "showline":  True,
        "linecolor": COLORS["border"],
        "linewidth": 1,
        "tickcolor": "#aaa",
        "tickfont":  {"family": _MONO, "size": 9, "color": "#aaa"},
        "title":     {"text": ""},
    },
    "yaxis": {
        "showgrid":  False,
        "showline":  False,
        "tickcolor": "#aaa",
        "tickfont":  {"family": _MONO, "size": 9, "color": "#aaa"},
        "title":     {"text": ""},
        "nticks":    4,
    },
    # Hover tooltip: IBM Plex Mono — the tooltip shows data values
    "hoverlabel": {
        "bgcolor":     "#ffffff",
        "bordercolor": "#e5e5e5",
        "font":        {"family": _MONO, "size": 11, "color": "#111"},
    },
    "margin":     {"l": 0, "r": 0, "t": 8, "b": 24},
    # Legend labels describe chart series — Inter as UI chrome
    "legend":     {"font": {"family": _SANS, "size": 10, "color": "#888"}, "bgcolor": "rgba(0,0,0,0)", "borderwidth": 0},
    "showlegend": False,
}


def empty_figure(message="No data"):
    """
    Blank placeholder figure shown when data is loading or a filter returns nothing.

    Parameters
    ----------
    message : str  Text centered in the empty chart area
    """
    fig = go.Figure()
    fig.update_layout(**CHART_THEME)
    fig.update_layout(
        xaxis={"visible": False},
        yaxis={"visible": False},
        annotations=[{
            "text":      message,
            "showarrow": False,
            "font":      {"size": 12, "color": "#aaa"},
            "xref":      "paper",
            "yref":      "paper",
            "x":         0.5,
            "y":         0.5,
        }],
    )
    return fig


def phase_bar(df, player_col, metric_col, color="blue", title=""):
    """
    Horizontal bar chart for phase batting leaderboards.

    Parameters
    ----------
    df         : DataFrame  One row per player
    player_col : str        Column for player names (y-axis)
    metric_col : str        Column for the ranked metric (x-axis)
    color      : str        COLORS key for bar fill, e.g. "blue" | "green" | "orange"
    title      : str        Chart title
    """
    if df is None or df.empty:
        return empty_figure("No data for selected filters")

    fig = go.Figure(go.Bar(
        x=df[metric_col],
        y=df[player_col],
        orientation="h",
        marker_color=COLORS.get(color, COLORS["blue"]),
        marker_line_width=0,
        width=0.5,
    ))
    fig.update_layout(**CHART_THEME)
    fig.update_layout(
        yaxis={"autorange": "reversed"},
        margin={"l": 110, "r": 0, "t": 8, "b": 24},
    )
    return fig


def phase_stacked_bar(df, x_col, pp_col, mid_col, death_col, title=""):
    """
    Stacked bar chart breaking innings runs into powerplay / middle / death segments.
    Powerplay = blue, middle = green, death = orange.

    Parameters
    ----------
    df        : DataFrame  One row per match or team
    x_col     : str        Column for x-axis labels (e.g. season or team name)
    pp_col    : str        Column for powerplay run contribution
    mid_col   : str        Column for middle overs run contribution
    death_col : str        Column for death overs run contribution
    title     : str        Chart title
    """
    if df is None or df.empty:
        return empty_figure()

    fig = go.Figure([
        go.Bar(name="Powerplay", x=df[x_col], y=df[pp_col],    marker_color=COLORS["blue"],   marker_line_width=0, width=0.5),
        go.Bar(name="Middle",    x=df[x_col], y=df[mid_col],   marker_color=COLORS["green"],  marker_line_width=0, width=0.5),
        go.Bar(name="Death",     x=df[x_col], y=df[death_col], marker_color=COLORS["orange"], marker_line_width=0, width=0.5),
    ])
    fig.update_layout(**CHART_THEME)
    fig.update_layout(
        barmode="stack",
        showlegend=True,
        yaxis={"visible": False},
    )
    return fig


def win_probability_line(df, over_col, prob_col, title=""):
    """
    Line chart showing win probability over overs in a match.
    Primary line: solid #111, 1.5px. Reference line: dashed #f97316, 60% opacity.

    Parameters
    ----------
    df       : DataFrame  One row per over
    over_col : str        Column for over number (x-axis)
    prob_col : str        Column for win probability 0.0-1.0 (y-axis)
    title    : str        Chart title
    """
    if df is None or df.empty:
        return empty_figure("No match selected")

    fig = go.Figure()
    fig.add_hline(y=0.5, line_dash="dash", line_color=COLORS["orange"], line_width=1, opacity=0.6)
    fig.add_trace(go.Scatter(
        x=df[over_col],
        y=df[prob_col],
        mode="lines",
        line={"color": COLORS["text"], "width": 1.5},
        fill=None,
    ))
    fig.update_layout(**CHART_THEME)
    fig.update_layout(
        xaxis={"showline": False},
        yaxis={"tickformat": ".0%", "range": [0, 1]},
    )
    return fig


def win_probability_gauge(prob, title="Win Probability"):
    """
    Semi-circular gauge for the match simulator page.
    Background zones: light red 0-40%, neutral 40-60%, light green 60-100%.

    Parameters
    ----------
    prob  : float  Predicted win probability, 0.0 to 1.0
    title : str    Label displayed above the gauge
    """
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=round(prob * 100, 1),
        number={"suffix": "%", "font": {"size": 32, "color": "#111", "family": "Inter, system-ui, sans-serif"}},
        gauge={
            "axis":        {"range": [0, 100], "tickwidth": 1, "tickcolor": "#aaa", "tickfont": {"size": 10}},
            "bar":         {"color": COLORS["blue"], "thickness": 0.2},
            "bgcolor":     "#f5f5f5",
            "borderwidth": 0,
            "steps": [
                {"range": [0,  40],  "color": "#fef2f0"},
                {"range": [40, 60],  "color": "#fafafa"},
                {"range": [60, 100], "color": "#f0faf4"},
            ],
        },
        title={"text": title, "font": {"size": 9, "color": "#888", "family": "Inter, system-ui, sans-serif"}},
    ))
    fig.update_layout(**CHART_THEME)
    fig.update_layout(
        height=260,
        margin={"t": 40, "r": 20, "b": 10, "l": 20},
    )
    return fig


def matchup_heatmap(df, x_col, y_col, value_col, title=""):
    """
    Diverging heatmap for bowler-batsman matchup matrix.
    Low values (batsman struggles) = green. High values (batsman dominates) = orange.

    Parameters
    ----------
    df        : DataFrame  Long format, one row per matchup
    x_col     : str        Column for x-axis labels (bowler name or bowler type)
    y_col     : str        Column for y-axis labels (batsman name)
    value_col : str        Column for cell values (e.g. "strike_rate")
    title     : str        Chart title
    """
    if df is None or df.empty:
        return empty_figure("No matchup data")

    pivot = df.pivot(index=y_col, columns=x_col, values=value_col)
    fig = go.Figure(go.Heatmap(
        z=pivot.values,
        x=pivot.columns.tolist(),
        y=pivot.index.tolist(),
        colorscale=[
            [0.0, COLORS["green"]],
            [0.5, "#ffffff"],
            [1.0, COLORS["orange"]],
        ],
        showscale=True,
    ))
    fig.update_layout(**CHART_THEME)
    fig.update_layout(margin={"l": 120, "r": 0, "t": 8, "b": 24})
    return fig


def venue_bar(df, venue_col, metric_col, title=""):
    """
    Vertical bar chart for venue scoring rate comparison.
    Bars at or above the dataset mean are blue; below are orange.

    Parameters
    ----------
    df         : DataFrame  One row per venue
    venue_col  : str        Column for venue names (x-axis)
    metric_col : str        Column for the metric (y-axis, e.g. "run_rate")
    title      : str        Chart title
    """
    if df is None or df.empty:
        return empty_figure("No venue data")

    mean_val   = df[metric_col].mean()
    bar_colors = [COLORS["blue"] if v >= mean_val else COLORS["orange"] for v in df[metric_col]]

    fig = go.Figure(go.Bar(
        x=df[venue_col],
        y=df[metric_col],
        marker_color=bar_colors,
        marker_line_width=0,
        width=0.5,
    ))
    fig.update_layout(**CHART_THEME)
    return fig
