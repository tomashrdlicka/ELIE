import os

import dash
from dash import html, dcc, Input, Output
import dash_bootstrap_components as dbc

app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])

app.layout = html.Div([
    dbc.Button("Click Me", id="my-button", n_clicks=0),
    html.Div(id="output-div")
])


@app.callback(
    Output("output-div", "children"),
    Input("my-button", "n_clicks")
)
def update_output(n_clicks):
    if n_clicks > 0:
        print("Hello World")
        return f"You have clicked the button {n_clicks} times."
    return "Click the button to see the output."


if __name__ == "__main__":
    # common: pick up whatever PORT Replit (or any host) gives you
    port = int(os.environ.get("PORT", 8050))
    # if we're on Replit deployment, bind 0.0.0.0; otherwise default host
    is_replit = bool(os.environ.get("REPLIT_DEPLOYMENT"))
    host = "0.0.0.0" if is_replit else "127.0.0.1"

    # debug locally, turn it off on Replit
    debug = not is_replit

    app.run(host=host, port=port, debug=debug)
