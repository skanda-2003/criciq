from dash import html


# Maps color name to hex — used only for the dynamic bar fill inline style.
# All other card styling lives in assets/style.css under .metric-card* selectors.
FILL_COLORS = {
    "blue":   "#3b82f6",  # runs, batting metrics
    "green":  "#22c55e",  # economy, positive metrics
    "orange": "#f97316",  # strike rate
    "red":    "#ef4444",  # dot balls, negative metrics
}


def metric_card(label, value, secondary=None, progress=None, color="blue"):
    """
    Reusable metric card matching the CricIQ design spec.

    Parameters
    ----------
    label     : str       ALL-CAPS label shown above the number, e.g. "Total Matches"
    value     : str       Large bold primary number, e.g. "1,175"
    secondary : str|None  Smaller value shown inline next to the big number, e.g. "/7"
    progress  : int|None  0-100 fill percentage for the bar; omit to hide the bar entirely
    color     : str       Bar fill color: "blue" | "green" | "orange" | "red"
    """
    fill_color = FILL_COLORS.get(color, FILL_COLORS["blue"])

    value_row = html.Div([
        html.Span(value, className="metric-card__value"),
        html.Span(secondary, className="metric-card__secondary") if secondary else None,
    ], className="metric-card__value-row")

    bar = None
    if progress is not None:
        bar = html.Div(
            html.Div(className="metric-card__bar-fill", style={
                "width":           f"{progress}%",
                "backgroundColor": fill_color,
            }),
            className="metric-card__bar-track",
        )

    return html.Div([
        html.Span(label, className="metric-card__label"),
        value_row,
        bar,
    ], className="metric-card")
