from dash import html
import dash_bootstrap_components as dbc
import dash



def create_navbar():
    """
    Returns the top navigation bar for CricIQ.

    Layout: brand name left | compact dataset stats inline | page links right | season toggle.
    Height is 48px, background #0f0f0f, no border or shadow.
    All visual rules live in assets/style.css under .ciq-navbar* selectors.
    dbc.NavLink is used for nav links only - active="exact" adds .active
    automatically when the URL matches, which style.css targets for white color.
    """
    return html.Nav([

        html.A("CricIQ", href="/", className="ciq-navbar__brand"),

        html.Span("1,243 matches · 295,732 deliveries", className="ciq-navbar__stats"),

        html.Div([
            dbc.NavLink("Overview",     href="/",             active="exact", className="ciq-navbar__nav-link"),
            dbc.NavLink("Player",       href="/player",       active="exact", className="ciq-navbar__nav-link"),
            dbc.NavLink("Batters",      href="/batters",      active="exact", className="ciq-navbar__nav-link"),
            dbc.NavLink("Bowlers",      href="/bowlers",      active="exact", className="ciq-navbar__nav-link"),
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
