import dash
from dash import dcc, html, Input, Output, State
import plotly.graph_objs as go
import numpy as np
import random

app = dash.Dash(__name__)
server = app.server

# === FAKE GRAPH DATA ===
FAKE_GRAPH = {
    "start": [f"start_child_{i}" for i in range(4)]
}

# App State
graph_tree = {"start": None}
clicked_nodes = set()
visible_nodes = {"start", *FAKE_GRAPH["start"]}


def generate_children(term, count=3):
    """Generate and register children if not already present."""
    if term not in FAKE_GRAPH:
        FAKE_GRAPH[term] = [f"{term}_child_{i}" for i in range(count)]
    children = FAKE_GRAPH[term]
    for child in children:
        graph_tree.setdefault(child, term)
    return children


def build_positions(visible, root_term, spacing=3.0):
    """Compute layout from given root for visible nodes only."""
    positions = {}

    def dfs(node, depth=0, angle=0.0, spread=np.pi * 2):
        if node not in visible or node in positions:
            return

        r = spacing * depth
        x = r * np.cos(angle)
        y = r * np.sin(angle)
        positions[node] = (x, y)

        children = FAKE_GRAPH.get(node, [])
        visible_children = [c for c in children if c in visible]
        N = len(visible_children)
        for i, child in enumerate(visible_children):
            child_angle = angle + spread * ((i - (N - 1) / 2) / max(N, 1))
            dfs(child, depth + 1, child_angle, spread / 2)

    dfs(root_term)
    return positions


def generate_figure(root_term="start"):
    global visible_nodes, clicked_nodes

    node_positions = build_positions(visible_nodes, root_term)

    xs, ys, labels, colors = [], [], [], []
    for word, (x, y) in node_positions.items():
        xs.append(x)
        ys.append(y)
        labels.append(word)
        colors.append("red" if word in clicked_nodes else "blue")

    trace = go.Scatter(
        x=xs,
        y=ys,
        mode="markers+text",
        text=labels,
        textposition="top center",
        marker=dict(size=18, color=colors),
        customdata=labels,
        hoverinfo="text"
    )

    layout = go.Layout(
        title="🧠 Concept Tree Explorer (Iterative)",
        clickmode="event+select",
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
        margin=dict(l=20, r=20, t=40, b=20),
        height=700
    )

    return go.Figure(data=[trace], layout=layout)


# === Dash Layout ===
app.layout = html.Div([
    html.H3("🧠 Semantic Tree Explorer"),

    html.Div([
        html.Button("Reset Graph", id="reset-btn", n_clicks=0),
        dcc.Input(id="start-input", type="text", placeholder="Enter root concept...", debounce=True),
        html.Button("Submit", id="submit-btn", n_clicks=0),
    ], style={"display": "flex", "gap": "10px", "alignItems": "center", "marginBottom": "20px"}),

    dcc.Graph(id="graph", figure=generate_figure()),
    dcc.Store(id="last-clicked", data="start"),

    html.Div(
        id="info-box",
        children=[
            html.H4("ℹ️ About Quaternions"),
            html.P(
                "Quaternions are a number system that extends complex numbers. "
                "They are commonly used to represent rotations in 3D space, as they avoid gimbal lock "
                "and provide smooth interpolation (slerp). A quaternion is composed of one real part and "
                "three imaginary parts: q = w + xi + yj + zk."
            )
        ],
        style={
            "border": "1px solid #ccc",
            "padding": "15px",
            "marginTop": "20px",
            "backgroundColor": "#f9f9f9",
            "borderRadius": "8px"
        }
    )
])


@app.callback(
    Output("graph", "figure"),
    Output("last-clicked", "data"),
    Input("graph", "clickData"),
    Input("reset-btn", "n_clicks"),
    Input("submit-btn", "n_clicks"),
    State("start-input", "value"),
    State("last-clicked", "data")
)
def handle_interaction(clickData, reset_clicks, submit_clicks, user_input, last_clicked):
    global visible_nodes, clicked_nodes, FAKE_GRAPH, graph_tree

    ctx = dash.callback_context
    trigger_id = ctx.triggered[0]["prop_id"].split(".")[0] if ctx.triggered else None

    # === Reset Button ===
    if trigger_id == "reset-btn":
        FAKE_GRAPH = {"start": [f"start_child_{i}" for i in range(4)]}
        graph_tree = {"start": None}
        clicked_nodes = set()
        visible_nodes = {"start", *FAKE_GRAPH["start"]}
        return generate_figure("start"), "start"

    # === Submit New Root Term ===
    if trigger_id == "submit-btn" and user_input:
        term = user_input.strip()
        children = [f"{term}_{i}" for i in range(4)]
        FAKE_GRAPH = {term: children}
        graph_tree = {term: None}
        clicked_nodes = set()
        visible_nodes = {term, *children}
        return generate_figure(term), term

    # === Node Click ===
    if clickData and "points" in clickData:
        clicked = clickData["points"][0]["customdata"]
        if clicked not in clicked_nodes:
            clicked_nodes.add(clicked)
            children = generate_children(clicked)
            visible_nodes.update(children)
        return generate_figure(last_clicked), clicked

    return generate_figure(last_clicked), last_clicked


if __name__ == "__main__":
    app.run(debug=True)
