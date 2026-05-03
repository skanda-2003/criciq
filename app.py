import dash
from dash import html, dcc, callback, Input, Output, ctx
import dash_bootstrap_components as dbc

from components.navbar import create_navbar

app = dash.Dash(
    __name__,
    use_pages=True,
    external_stylesheets=[dbc.themes.BOOTSTRAP],
    suppress_callback_exceptions=True,
    meta_tags=[{"name": "viewport", "content": "width=device-width, initial-scale=1"}],
)

app.layout = html.Div([
    # Store lives outside the page container so it persists across page navigation.
    # Initial value = 2021-26 (the default analysis window).
    dcc.Store(id="season-filter", data={"min": 2021, "max": 2026}),
    create_navbar(),
    html.Div(dash.page_container, className="page-wrapper"),
])


@callback(
    Output("season-filter",      "data"),
    Output("btn-season-recent",  "className"),
    Output("btn-season-all",     "className"),
    Input("btn-season-recent",   "n_clicks"),
    Input("btn-season-all",      "n_clicks"),
    prevent_initial_call=True,
)
def update_season_filter(n_recent, n_all):
    # ctx.triggered_id is the id of whichever button was just clicked
    if ctx.triggered_id == "btn-season-all":
        return {"min": 2008, "max": 2026}, "season-btn", "season-btn season-btn--active"
    return {"min": 2021, "max": 2026}, "season-btn season-btn--active", "season-btn"


if __name__ == "__main__":
    app.run(debug=True)
