# Generate the skeleton of a basiv dash plotly app
# The app should have a single button, which when clicked prints "Hello World" to the console
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
    app.run(debug=True)
