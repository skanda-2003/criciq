from dash import html
import dash_bootstrap_components as dbc
import dash


def _stat_block(label, value):
    """
    Single label/value unit shown in the navbar center strip.

    Parameters
    ----------
    label : str  Short dataset label, e.g. "Matches"
    value : str  Formatted value, e.g. "1,175"
    """
    return html.Div([
        html.Span(label, className="ciq-navbar__stat-label"),
        html.Span(value, className="ciq-navbar__stat-value"),
    ], className="ciq-navbar__stat-block")


def create_navbar():
    """
    Returns the top navigation bar for CricIQ.

    Layout: brand name left | dataset summary stats centered | page links right.
    Height is 48px, background #0f0f0f, no border or shadow.
    All visual rules live in assets/style.css under .ciq-navbar* selectors.
    dbc.NavLink is used for nav links only — active="exact" adds .active
    automatically when the URL matches, which style.css targets for white color.
    """
    return html.Nav([

        html.A("CricIQ", href="/", className="ciq-navbar__brand"),

        html.Div([
            _stat_block("Matches",    "1,175"),
            html.Span("|", className="ciq-navbar__divider"),
            _stat_block("Seasons",    "2008–2026"),
            html.Span("|", className="ciq-navbar__divider"),
            _stat_block("Deliveries", "279,586"),
        ], className="ciq-navbar__stats"),

        html.Div([
            dbc.NavLink("Overview",     href="/",             active="exact", className="ciq-navbar__nav-link"),
            dbc.NavLink("Batting",      href="/batting",      active="exact", className="ciq-navbar__nav-link"),
            dbc.NavLink("Player",       href="/player",       active="exact", className="ciq-navbar__nav-link"),
            dbc.NavLink("Bowlers",      href="/bowler",       active="exact", className="ciq-navbar__nav-link"),
            dbc.NavLink("Allrounders",  href="/allrounders",  active="exact", className="ciq-navbar__nav-link"),
            dbc.NavLink("Simulator",    href="/simulator",    active="exact", className="ciq-navbar__nav-link"),
            dbc.NavLink("Head-to-Head", href="/head-to-head", active="exact", className="ciq-navbar__nav-link"),
            dbc.NavLink("Teams",        href="/team",         active="exact", className="ciq-navbar__nav-link"),
        ], className="ciq-navbar__nav"),

        # Season filter toggle - persists across all pages via dcc.Store in app.py
        html.Div([
            html.Button("2021-26", id="btn-season-recent", className="season-btn season-btn--active", n_clicks=0),
            html.Button("All time", id="btn-season-all",   className="season-btn",                    n_clicks=0),
        ], className="ciq-navbar__season-toggle"),

    ], className="ciq-navbar")
