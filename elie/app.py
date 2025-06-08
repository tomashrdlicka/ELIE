import dash
from dash import dcc, html, Input, Output, State
import plotly.graph_objs as go
import numpy as np
import random
import json
from dash import ctx
import base64

app = dash.Dash(__name__)
server = app.server

# === Graph State ===
# Initialization moved after function definitions

explanation_paragraph = (
    "Quaternions are a number system that extends complex numbers. "
    "They are commonly used to represent rotations in 3D space, as they avoid gimbal lock "
    "and provide smooth interpolation (slerp). A quaternion is composed of one real part and "
    "three imaginary parts: q = w + xi + yj + zk."
)

def generate_children(term, count=3):
    """Generate 3 children and store in node_data with normalized distance."""
    if term not in node_data:
        return []

    existing_children = [k for k, v in node_data.items() if v["parent"] == term]
    if existing_children:
        return existing_children  # Already added

    total = len(node_data) + count
    for i in range(count):
        child = f"{term}_child_{i}"
        raw_dist = round(random.uniform(0.5, 1.5), 2)
        norm_dist = raw_dist / total * 6
        norm_dist = max(0.1, min(1.0, round(norm_dist * 10) / 10))
        raw_breadth = round(random.uniform(0.5, 1.5), 2)
        norm_breadth = raw_breadth / total * 6
        norm_breadth = max(0.1, min(1.0, round(norm_breadth * 10) / 10))
        node_data[child] = {
            "parent": term,
            "distance": norm_dist,
            "raw_distance": raw_dist,
            "breadth": norm_breadth,
            "raw_breadth": raw_breadth
        }
    recompute_all_distances()
    return [f"{term}_child_{i}" for i in range(count)]

def recompute_all_distances():
    total = len(node_data)
    for node, data in node_data.items():
        if data["parent"] is not None:
            # Distance
            raw_dist = data.get("raw_distance", data["distance"])
            norm_dist = raw_dist / total * 6
            norm_dist = max(0.1, min(1.0, round(norm_dist * 10) / 10))
            data["distance"] = norm_dist
            # Breadth
            raw_breadth = data.get("raw_breadth", data.get("breadth", 1.0))
            norm_breadth = raw_breadth / total * 6
            norm_breadth = max(0.1, min(1.0, round(norm_breadth * 10) / 10))
            data["breadth"] = norm_breadth

def build_positions(base_spacing=3.0):
    positions = {}

    def dfs(node, depth=0, angle=0.0, spread=np.pi * 2):
        if node in positions:
            return

        if node == "start":
            x, y = 0, 0
        else:
            parent = node_data[node]["parent"]
            dist = node_data[node]["distance"]
            px, py = positions.get(parent, (0, 0))
            r = base_spacing * dist
            x = px + r * np.cos(angle)
            y = py + r * np.sin(angle)

        positions[node] = (x, y)

        # Explore children
        children = [k for k, v in node_data.items() if v["parent"] == node]
        N = len(children)
        for i, child in enumerate(children):
            child_angle = angle + spread * ((i - (N - 1) / 2) / max(N, 1))
            dfs(child, depth + 1, child_angle, spread / 2)

    dfs("start")
    return positions

def rescale_positions(positions, target_radius=10.0):
    # Get all non-root positions
    non_root_positions = [(x, y) for node, (x, y) in positions.items() if (x, y) != (0, 0)]
    if not non_root_positions:
        return positions  # Only root node exists
    max_dist = max(np.hypot(x, y) for x, y in non_root_positions)
    if max_dist == 0:
        return positions  # All nodes at root
    scale = target_radius / max_dist
    return {node: (x * scale, y * scale) for node, (x, y) in positions.items()}

def generate_figure():
    positions = build_positions()
    positions = rescale_positions(positions, target_radius=10.0)
    xs, ys, labels, colors = [], [], [], []
    edge_xs, edge_ys = [], []
    sizes = []

    for node, (x, y) in positions.items():
        xs.append(x)
        ys.append(y)
        if node == "start" and "label" in node_data[node]:
            label = node_data[node]["label"]
        else:
            label = node
        parent = node_data[node]["parent"]
        breadth = node_data[node].get("breadth", 1.0)
        if parent:
            dist = node_data[node]["distance"]
            label += f" ({dist}, {breadth})"
            if parent in positions:
                px, py = positions[parent]
                edge_xs += [px, x, None]
                edge_ys += [py, y, None]
        elif node != "start":
            label += f" ({breadth})"
        sizes.append(80 * breadth)
        labels.append(label)
        if node == "start":
            colors.append("black")
        elif node in clicked_nodes:
            colors.append("#02ab13")  # dark olive green
        else:
            colors.append("#d3d3d3")  # light grey

    # Compute centroid
    center_x = sum(xs) / len(xs)
    center_y = sum(ys) / len(ys)
    spread = max(
        max(xs) - min(xs),
        max(ys) - min(ys),
    ) / 2 + 2

    x_range = [center_x - spread, center_x + spread]
    y_range = [center_y - spread, center_y + spread]

    edge_trace = go.Scatter(
        x=edge_xs,
        y=edge_ys,
        mode="lines",
        line=dict(width=2, color="#888"),
        hoverinfo="none"
    )

    node_trace = go.Scatter(
        x=xs,
        y=ys,
        mode="markers+text",
        text=labels,
        textposition="top center",
        marker=dict(
            size=sizes,
            color=colors,
            opacity=1,
            line=dict(width=2, color='white')
        ),
        customdata=list(positions.keys()),
        hoverinfo="text",
        selected=dict(marker=dict(opacity=1)),
        unselected=dict(marker=dict(opacity=1))
    )

    layout = go.Layout(
        clickmode="event+select",
        xaxis=dict(visible=False, range=x_range),
        yaxis=dict(visible=False, range=y_range),
        margin=dict(l=20, r=20, t=40, b=20),
        height=700,
        transition={'duration': 500, 'easing': 'cubic-in-out'},
        showlegend=False,
        plot_bgcolor='white',
        paper_bgcolor='white',
        shapes=[dict(
            type='rect',
            xref='paper', yref='paper',
            x0=0, y0=0, x1=1, y1=1,
            line=dict(color='black', width=2),
            fillcolor='rgba(0,0,0,0)'
        )]
    )

    return go.Figure(data=[edge_trace, node_trace], layout=layout)

# === Graph State ===
# Initialize with 'start' and 4 children
node_data = {
    "start": {"parent": None, "distance": 0.0}
}
total = 5  # 1 root + 4 children
for i in range(4):
    child = f"start_child_{i}"
    raw_dist = round(random.uniform(0.5, 1.5), 2)
    norm_dist = raw_dist / total * 6
    norm_dist = max(0.1, min(1.0, round(norm_dist * 10) / 10))
    raw_breadth = round(random.uniform(0.5, 1.5), 2)
    norm_breadth = raw_breadth / total * 6
    norm_breadth = max(0.1, min(1.0, round(norm_breadth * 10) / 10))
    node_data[child] = {
        "parent": "start",
        "distance": norm_dist,
        "raw_distance": raw_dist,
        "breadth": norm_breadth,
        "raw_breadth": raw_breadth
    }
clicked_nodes = set()
unclicked_nodes = [k for k in node_data.keys() if k != "start"]
clicked_nodes_list = []
recompute_all_distances()

# === Dash Layout ===
app.layout = html.Div([
    html.H2(
        "ELIE (Explain Like I'm an Expert)",
        style={
            "textAlign": "center",
            "width": "100%",
            "marginBottom": "18px"
        }
    ),

    html.Div([
        html.Button(
            "Reset Graph",
            id="reset-btn",
            n_clicks=0,
            style={
                "padding": "10px 22px",
                "fontSize": "1.08em",
                "borderRadius": "7px",
                "backgroundColor": "#e0e7ef",
                "border": "1px solid #b0b8c1",
                "color": "#222",
                "cursor": "pointer",
                "transition": "background 0.2s, color 0.2s"
            }
        ),
        dcc.Input(
            id="start-input",
            type="text",
            placeholder="Enter root concept...",
            debounce=True,
            n_submit=0,
            style={
                "padding": "10px 22px",
                "fontSize": "1.08em",
                "borderRadius": "7px",
                "backgroundColor": "#e0e7ef",
                "border": "1px solid #b0b8c1",
                "color": "#222",
                "transition": "background 0.2s, color 0.2s"
            }
        ),
        html.Button(
            "Submit",
            id="submit-btn",
            n_clicks=0,
            style={
                "padding": "10px 22px",
                "fontSize": "1.08em",
                "borderRadius": "7px",
                "backgroundColor": "#e0e7ef",
                "border": "1px solid #b0b8c1",
                "color": "#222",
                "cursor": "pointer",
                "transition": "background 0.2s, color 0.2s"
            }
        ),
    ], style={"display": "flex", "gap": "10px", "alignItems": "center", "marginBottom": "20px"}),

    html.Div([
        dcc.Graph(id="graph", figure=generate_figure(), style={"flex": "3 1 0%"}),
        html.Div([
            html.Div([
                html.Button(
                    "Save Graph",
                    id="save-btn",
                    n_clicks=0,
                    style={
                        "padding": "10px 22px",
                        "fontSize": "1.08em",
                        "borderRadius": "7px",
                        "backgroundColor": "#e0e7ef",
                        "border": "1px solid #b0b8c1",
                        "color": "#222",
                        "cursor": "pointer",
                        "transition": "background 0.2s, color 0.2s"
                    }
                ),
                dcc.Download(id="download-graph"),
                dcc.Upload(
                    id="upload-graph",
                    children=html.Button(
                        "Load Graph",
                        style={
                            "padding": "10px 22px",
                            "fontSize": "1.08em",
                            "borderRadius": "7px",
                            "backgroundColor": "#e0e7ef",
                            "border": "1px solid #b0b8c1",
                            "color": "#222",
                            "cursor": "pointer",
                            "transition": "background 0.2s, color 0.2s",
                            "marginLeft": "10px"
                        }
                    ),
                    multiple=False
                ),
            ], style={"marginBottom": "16px", "display": "flex", "gap": "10px", "justifyContent": "center"}),
            html.Div(
                id="info-box",
                children=[
                    html.H4("ℹ️ About Quaternions"),
                    html.P(explanation_paragraph),
                    html.Div(id="knowledge-box")
                ],
                style={
                    "border": "1px solid #ccc",
                    "padding": "15px",
                    "backgroundColor": "#f9f9f9",
                    "borderRadius": "8px",
                    "flex": "1 1 0%",
                    "maxWidth": "350px",
                    "minWidth": "220px",
                    "marginTop": "0px",
                    "marginLeft": "20px",
                    "marginRight": "30px"
                }
            )
        ], style={"display": "flex", "flexDirection": "column", "alignItems": "stretch", "flex": "1 1 0%"})
    ], style={"display": "flex", "flexDirection": "row", "alignItems": "flex-start"}),
    
    dcc.Store(id="last-clicked", data="start"),
])

@app.callback(
    Output("graph", "figure"),
    Output("last-clicked", "data"),
    Output("info-box", "children"),
    Output("upload-graph", "contents"),
    Input("graph", "clickData"),
    Input("reset-btn", "n_clicks"),
    Input("submit-btn", "n_clicks"),
    Input("start-input", "n_submit"),
    Input("upload-graph", "contents"),
    State("start-input", "value"),
    State("last-clicked", "data")
)
def handle_interaction(clickData, reset_clicks, submit_clicks, input_submit, upload_contents, user_input, last_clicked):
    global node_data, clicked_nodes, unclicked_nodes, clicked_nodes_list, explanation_paragraph

    ctx = dash.callback_context
    trigger_id = ctx.triggered[0]["prop_id"].split(".")[0] if ctx.triggered else None

    # --- Load logic ---
    if trigger_id == "upload-graph" and upload_contents is not None:
        content_type, content_string = upload_contents.split(',')
        decoded = base64.b64decode(content_string)
        data = json.loads(decoded.decode('utf-8'))
        node_data = data["node_data"]
        clicked_nodes = set(clicked_nodes_list := data["clicked_nodes_list"])
        unclicked_nodes = data["unclicked_nodes"]
        explanation_paragraph = data.get("explanation", explanation_paragraph)
        recompute_all_distances()
        info_box_children = [
            html.H4("ℹ️ About Quaternions"),
            html.P(explanation_paragraph),
            html.Div(id="knowledge-box")
        ]
        return generate_figure(), "start", info_box_children, None

    # --- Reset logic ---
    if trigger_id == "reset-btn":
        node_data = {
            "start": {"parent": None, "distance": 0.0}
        }
        total = 5  # 1 root + 4 children
        for i in range(4):
            child = f"start_child_{i}"
            raw_dist = round(random.uniform(0.5, 1.5), 2)
            norm_dist = raw_dist / total * 6
            norm_dist = max(0.1, min(1.0, round(norm_dist * 10) / 10))
            raw_breadth = round(random.uniform(0.5, 1.5), 2)
            norm_breadth = raw_breadth / total * 6
            norm_breadth = max(0.1, min(1.0, round(norm_breadth * 10) / 10))
            node_data[child] = {
                "parent": "start",
                "distance": norm_dist,
                "raw_distance": raw_dist,
                "breadth": norm_breadth,
                "raw_breadth": raw_breadth
            }
        recompute_all_distances()
        clicked_nodes = set()
        unclicked_nodes = [k for k in node_data.keys() if k != "start"]
        clicked_nodes_list = []
        info_box_children = [
            html.H4("ℹ️ About Quaternions"),
            html.P(explanation_paragraph),
            html.Div(id="knowledge-box")
        ]
        return generate_figure(), "start", info_box_children, dash.no_update

    # --- Submit logic ---
    if (trigger_id == "submit-btn" or trigger_id == "start-input") and user_input:
        term = user_input.strip()
        node_data = {
            "start": {"parent": None, "distance": 0.0, "label": term}
        }
        total = 5  # 1 root + 4 children
        for i in range(4):
            child = f"start_child_{i}"
            raw_dist = round(random.uniform(0.5, 1.5), 2)
            norm_dist = raw_dist / total * 6
            norm_dist = max(0.1, min(1.0, round(norm_dist * 10) / 10))
            raw_breadth = round(random.uniform(0.5, 1.5), 2)
            norm_breadth = raw_breadth / total * 6
            norm_breadth = max(0.1, min(1.0, round(norm_breadth * 10) / 10))
            node_data[child] = {
                "parent": "start",
                "distance": norm_dist,
                "raw_distance": raw_dist,
                "breadth": norm_breadth,
                "raw_breadth": raw_breadth
            }
        recompute_all_distances()
        clicked_nodes = set()
        unclicked_nodes = [k for k in node_data.keys() if k != "start"]
        clicked_nodes_list = []
        info_box_children = [
            html.H4("ℹ️ About Quaternions"),
            html.P(explanation_paragraph),
            html.Div(id="knowledge-box")
        ]
        return generate_figure(), "start", info_box_children, dash.no_update

    # --- Click logic ---
    if clickData and "points" in clickData:
        point = clickData["points"][0]
        clicked = point.get("customdata")
        if not clicked:
            return generate_figure(), last_clicked, dash.no_update, dash.no_update
        if clicked == "start" and clicked in clicked_nodes:
            return generate_figure(), clicked, dash.no_update, dash.no_update

        if clicked not in clicked_nodes:
            clicked_nodes.add(clicked)
            if clicked in unclicked_nodes:
                unclicked_nodes.remove(clicked)
            if clicked not in clicked_nodes_list:
                clicked_nodes_list.append(clicked)
            children = generate_children(clicked)
            for c in children:
                if c not in unclicked_nodes and c not in clicked_nodes_list:
                    unclicked_nodes.append(c)
        return generate_figure(), clicked, dash.no_update, dash.no_update

    # --- Default ---
    return generate_figure(), last_clicked, dash.no_update, dash.no_update

@app.callback(
    Output("knowledge-box", "children"),
    [Input("graph", "figure")]
)
def update_knowledge_box(_):
    known = clicked_nodes_list
    unknown = unclicked_nodes
    return [
        html.Div([
            html.H5("Known"),
            html.Ul([html.Li(k) for k in known]) if known else html.P("None")
        ], style={"marginBottom": "10px"}),
        html.Div([
            html.H5("Unknown"),
            html.Ul([html.Li(u) for u in unknown]) if unknown else html.P("None")
        ])
    ]

@app.callback(
    Output("download-graph", "data"),
    Input("save-btn", "n_clicks"),
    prevent_initial_call=True
)
def save_graph(n_clicks):
    if n_clicks:
        export_data = {
            "node_data": node_data,
            "clicked_nodes_list": clicked_nodes_list,
            "unclicked_nodes": unclicked_nodes,
            "explanation": explanation_paragraph  # define this variable
        }
        return dict(
            content=json.dumps(export_data, indent=2),
            filename="elie_graph.json"
        )
    return dash.no_update

if __name__ == "__main__":
    app.run(debug=True)








