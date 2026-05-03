import dash
from dash import html
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
    create_navbar(),
    html.Div(dash.page_container, className="page-wrapper"),
])

if __name__ == "__main__":
    app.run(debug=True)
