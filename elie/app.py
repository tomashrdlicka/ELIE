import os
import dash
from dash import dcc, html, Input, Output, State
import plotly.graph_objs as go
import numpy as np
import random
import json
from dash import ctx
import base64
from elie.llm_calls import call_modal_llm, build_starter_prompt, parse_terms, build_further_prompt, build_final_prompt
import os

app = dash.Dash(__name__)
server = app.server

# === Graph State ===
# Initialize with only the center node and no children
node_data = {
    "start": {"parent": None, "distance": 0.0, "label": ""}
}
clicked_nodes = set()
unclicked_nodes = []
clicked_nodes_list = []

# Placeholder for the How It Works markdown (fill in from README)
HOW_IT_WORKS_MD = """## How It Works

1. **Pick a topic:** Type in something you want to learn—say, "quaternions".

2. **Get a baseline:** ELIE shows you an initial explanation and a web of related concepts (e.g. "complex numbers", "rotation", "linear algebra").

3. **Click what you know:** Select any familiar node—e.g. "linear algebra"—and ELIE refines the explanation.

4. **Iterate to expertise:** Keep choosing known concepts; the map updates and the explanation sharpens until it's perfectly pitched to your expertise.
"""


explanation_paragraph = HOW_IT_WORKS_MD

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

def build_positions(base_spacing=4.0):
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
    edge_colors = []
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
            if parent in positions:
                px, py = positions[parent]
                edge_xs += [px, x, None]
                edge_ys += [py, y, None]
                # Edge color: green if node is clicked, else gray
                if node in clicked_nodes:
                    edge_colors.append('rgba(2,171,19,0.35)')
                else:
                    edge_colors.append('#888')
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

    # Draw edges with per-segment color
    edge_traces = []
    edge_idx = 0
    for i in range(0, len(edge_xs), 3):
        color = edge_colors[edge_idx] if edge_idx < len(edge_colors) else '#888'
        edge_traces.append(go.Scatter(
            x=edge_xs[i:i+2],
            y=edge_ys[i:i+2],
            mode="lines",
            line=dict(width=2, color=color),
            hoverinfo="none",
            showlegend=False
        ))
        edge_idx += 1

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

    return go.Figure(data=edge_traces + [node_trace], layout=layout)

# === Dash Layout ===
app.layout = html.Div([
    html.H2(
        "ELIE (Explain Like I'm an Expert)",
        style={
            "textAlign": "left",
            "width": "100%",
            "marginLeft": "40px"
        }
    ),
    dcc.Store(id="input-overlay-visible", data=True),
    html.Div([
        # Graph and overlay input
        html.Div([
            dcc.Graph(id="graph", figure=generate_figure(), style={"flex": "3 1 0%", "position": "relative", "zIndex": 1}),
            # Overlay input centered on graph
            html.Div(
                dcc.Input(
                    id="start-input",
                    type="text",
                    placeholder="Enter root concept...",
                    debounce=True,
                    n_submit=0,
                    style={
                        "padding": "12px 28px",
                        "fontSize": "1.18em",
                        "borderRadius": "9px",
                        "backgroundColor": "#e0e7ef",
                        "border": "1.5px solid #b0b8c1",
                        "color": "#222",
                        "boxShadow": "0 2px 8px rgba(0,0,0,0.07)",
                        "outline": "none",
                        "width": "340px",
                        "textAlign": "center",
                        "marginTop": "4.5em",
                        "marginRight": "15.0em"
                    }
                ),
                id="centered-input-overlay",
                style={
                    "position": "fixed",
                    "left": "50%",
                    "top": "50%",
                    "transform": "translate(-70%, -50%)",
                    "zIndex": 10,
                    "pointerEvents": "auto"
                }
            ),
        ], style={"flex": "3 1 0%", "position": "relative", "minHeight": "700px"}),
        html.Div([
            html.Button(
                "Reset Term",
                id="reset-term-btn",
                n_clicks=0,
                style={
                    "padding": "10px 22px",
                    "fontSize": "1.08em",
                    "borderRadius": "7px",
                    "backgroundColor": "#e0e7ef",
                    "border": "1px solid #b0b8c1",
                    "color": "#222",
                    "cursor": "pointer",
                    "transition": "background 0.2s, color 0.2s",
                    "width": "auto%",
                    "display": "block",
                    "marginBottom": "10px"
                    
                }
            ),
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
                    html.H4("Welcome to ELIE!"),
                    dcc.Markdown(explanation_paragraph),
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
    [
        Output("graph", "figure"),
        Output("last-clicked", "data"),
        Output("info-box", "children"),
        Output("upload-graph", "contents"),
        Output("input-overlay-visible", "data"),
        Output("start-input", "value"),
    ],
    [
        Input("graph", "clickData"),
        Input("start-input", "n_submit"),
        Input("upload-graph", "contents"),
        Input("reset-term-btn", "n_clicks")
    ],
    [
        State("start-input", "value"),
        State("last-clicked", "data")
    ]
)
def handle_interaction(clickData, input_submit, upload_contents, reset_clicks, user_input, last_clicked):
    global node_data, clicked_nodes, unclicked_nodes, clicked_nodes_list, explanation_paragraph

    ctx = dash.callback_context
    trigger_id = ctx.triggered[0]["prop_id"].split(".")[0] if ctx.triggered else None

    # --- Reset logic ---
    if trigger_id == "reset-term-btn":
        node_data = {
            "start": {"parent": None, "distance": 0.0, "label": ""}
        }
        clicked_nodes.clear()
        unclicked_nodes.clear()
        clicked_nodes_list.clear()
        explanation_paragraph = HOW_IT_WORKS_MD
        info_box_children = [
            html.H4("Welcome to ELIE!"),
            dcc.Markdown(explanation_paragraph),
        ]
        return generate_figure(), "start", info_box_children, None, True, ""

    # --- Load logic ---
    if trigger_id == "upload-graph" and upload_contents is not None:
        content_type, content_string = upload_contents.split(',')
        decoded = base64.b64decode(content_string)
        data = json.loads(decoded.decode('utf-8'))
        node_data = data["node_data"]
        clicked_nodes = set(clicked_nodes_list := data["clicked_nodes_list"])
        unclicked_nodes = data["unclicked_nodes"]
        explanation_paragraph = data.get("explanation", HOW_IT_WORKS_MD)
        recompute_all_distances()
        info_box_children = [
            html.H4(f"About {node_data['start'].get('label', 'start')}"),
            dcc.Markdown(explanation_paragraph),
        ]
        return generate_figure(), "start", info_box_children, None, False, dash.no_update

    # --- Submit logic ---
    if trigger_id == "start-input" and user_input:
        term = user_input.strip()
        # Call LLM to get starter terms
        llm_response = call_modal_llm(build_starter_prompt(term))
        parsed_terms = parse_terms(llm_response, num_terms=4)  # Should return a dict like your starter_terms

        node_data = {
            "start": {"parent": None, "distance": 0.0, "label": term}
        }
        for child_term, props in parsed_terms.items():
            node_data[child_term] = {
                "parent": "start",
                "distance": props["distance"],
                "raw_distance": props["distance"],
                "breadth": props["breadth"],
                "raw_breadth": props["breadth"]
            }
        recompute_all_distances()
        clicked_nodes.clear()
        unclicked_nodes[:] = [k for k in node_data.keys() if k != "start"]
        clicked_nodes_list.clear()
        # Dynamically generate explanation paragraph
        explanation_paragraph = call_modal_llm(build_final_prompt(term, clicked_nodes_list, unclicked_nodes))
        info_box_children = [
            html.H4(f"About {term}"),
            dcc.Markdown(explanation_paragraph),
        ]
        return generate_figure(), "start", info_box_children, dash.no_update, False, dash.no_update

    # --- Click logic ---
    if clickData and "points" in clickData:
        point = clickData["points"][0]
        clicked = point.get("customdata")
        if not clicked:
            return generate_figure(), last_clicked, dash.no_update, dash.no_update, False, dash.no_update
        if clicked == "start" and clicked in clicked_nodes:
            return generate_figure(), clicked, dash.no_update, dash.no_update, False, dash.no_update

        if clicked not in clicked_nodes:
            clicked_nodes.add(clicked)
            if clicked in unclicked_nodes:
                unclicked_nodes.remove(clicked)
            if clicked not in clicked_nodes_list:
                clicked_nodes_list.append(clicked)

            # Dynamically call LLM for further prerequisites
            initial_term = node_data["start"].get("label", "start")
            known_terms = clicked_nodes_list.copy()
            unknown_terms = unclicked_nodes.copy()
            further_prompt = build_further_prompt(initial_term, unknown_terms, known_terms)
            llm_response = call_modal_llm(further_prompt)
            parsed_terms = parse_terms(llm_response, num_terms=3)  # Should return a dict

            # Add new children to the graph
            for child_term, props in parsed_terms.items():
                if child_term not in node_data:
                    node_data[child_term] = {
                        "parent": clicked,
                        "distance": props["distance"],
                        "raw_distance": props["distance"],
                        "breadth": props["breadth"],
                        "raw_breadth": props["breadth"]
                    }
                    if child_term not in unclicked_nodes and child_term not in clicked_nodes_list:
                        unclicked_nodes.append(child_term)

            recompute_all_distances()
            # Update explanation paragraph dynamically
            explanation_paragraph = call_modal_llm(build_final_prompt(initial_term, unclicked_nodes, clicked_nodes_list))
            info_box_children = [
                html.H4(f"About {initial_term}"),
                dcc.Markdown(explanation_paragraph),
            ]
            return generate_figure(), clicked, info_box_children, dash.no_update, False, dash.no_update

    # --- Default ---
    return generate_figure(), last_clicked, dash.no_update, dash.no_update, True, dash.no_update

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


@app.callback(
    Output("centered-input-overlay", "style"),
    Input("input-overlay-visible", "data"),
)
def toggle_overlay(visible):
    if visible:
        return {
            "position": "fixed",
            "left": "50%",
            "top": "50%",
            "transform": "translate(-60%, -30%)",
            "zIndex": 10,
            "pointerEvents": "auto"
        }
    else:
        return {"display": "none"}


if __name__ == "__main__":
    port = int(os.getenv("PORT", 8050))
    app.run(debug=True, port=port)
    app.run(
        debug=True,
        host="0.0.0.0",
        port=port,
    )
