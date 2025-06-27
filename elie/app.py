import os
import dash
from dash import dcc, html, Input, Output, State, ALL
import plotly.graph_objs as go
import numpy as np
import random
import json
from dash import ctx
import base64
from elie.gemini_calls import call_gemini_llm
from elie.prompting import build_starter_prompt, parse_terms, build_further_prompt, build_final_prompt
import time

app = dash.Dash(__name__)
server = app.server

# Inject CSS to remove body margin
app.index_string = """
<!DOCTYPE html>
<html>
    <head>
        {%metas%}
        <title>{%title%}</title>
        {%favicon%}
        {%css%}
        <style>
            html, body { margin: 0; padding: 0; height: 100%; width: 100%; background-color: #1a1a1a; }
            #_dash-root-content { height: 100%; }
        </style>
    </head>
    <body>
        {%app_entry%}
        <footer>
            {%config%}
            {%scripts%}
            {%renderer%}
        </footer>
    </body>
</html>
"""

# Placeholder for the How It Works markdown (fill in from README)
HOW_IT_WORKS_MD = """## How It Works

1. **Pick a topic:** Type in something you want to learn—say, "quaternions".

2. **Get a baseline:** ELIE shows you an initial explanation and a web of related concepts (e.g. "complex numbers", "rotation", "linear algebra").

3. **Click what you do not know:** Select any unfamiliar node—e.g. "linear algebra"—and ELIE refines the explanation.

4. **Iterate to expertise:** Keep choosing unknown concepts; the map updates and the explanation sharpens until it's perfectly pitched to your expertise.
"""

def get_initial_state():
    """Returns the default state for the application."""
    return {
        "node_data": {"start": {"parent": None, "distance": 0.0, "label": ""}},
        "clicked_nodes_list": [],
        "unclicked_nodes": [],
        "explanation_paragraph": HOW_IT_WORKS_MD,
        "last_clicked": "start"
    }

def recompute_all_distances(node_data):
    """Ensure all nodes have baseline distance and breadth values."""
    for node, data in node_data.items():
        # --- Breadth (node size) calculation ---
        if 'raw_breadth' not in data:
            # The start node is smaller than other nodes.
            data['raw_breadth'] = 0.8 if data['parent'] is None else 1.2
        data['breadth'] = data['raw_breadth']

        # --- Distance (edge length) calculation (only for non-root nodes) ---
        if data["parent"] is not None:
            if 'raw_distance' not in data:
                data['raw_distance'] = 1.0
            data['distance'] = data['raw_distance']

def build_positions(node_data, base_spacing=5.0, focus_node="start"):
    positions = {}
    focus_path = []
    curr = focus_node
    while curr and curr in node_data:
        focus_path.append(curr)
        curr = node_data[curr].get("parent")
    focus_path.reverse()

    def dfs(node, depth=0, angle=0.0, spread=np.pi * 2):
        if node in positions: return
        if node == "start": x, y = 0, 0
        else:
            parent = node_data[node]["parent"]
            dist = node_data[node]["distance"]
            px, py = positions.get(parent, (0, 0))
            r = base_spacing * dist
            x, y = px + r * np.cos(angle), py + r * np.sin(angle)
        positions[node] = (x, y)
        
        children = [k for k, v in node_data.items() if v["parent"] == node]
        if not children: return

        next_focus_node = None
        if node in focus_path:
            idx = focus_path.index(node)
            if idx + 1 < len(focus_path):
                next_focus_node = focus_path[idx + 1]

        weights = [3.0 if child == next_focus_node else 1.0 for child in children]
        total_weight = sum(weights)
        
        cursor = angle - spread / 2.0
        for i, child in enumerate(children):
            child_spread = spread * (weights[i] / total_weight)
            child_angle = cursor + child_spread / 2.0
            dfs(child, depth + 1, child_angle, child_spread)
            cursor += child_spread
    dfs("start")
    return positions

def apply_force_directed_layout(positions, node_data, iterations=100, k_attract=0.02, k_repel=0.2, base_spacing=5.0):
    """A force-directed layout simulation to optimize node placement."""
    nodes = list(positions.keys())
    
    # Run simulation for a number of iterations
    for _ in range(iterations):
        displacements = {node: np.array([0.0, 0.0]) for node in nodes}
        
        # 1. Repulsive forces between all pairs of nodes
        for i in range(len(nodes)):
            for j in range(i + 1, len(nodes)):
                u, v = nodes[i], nodes[j]
                pos_u, pos_v = np.array(positions[u]), np.array(positions[v])
                delta = pos_u - pos_v
                distance = np.linalg.norm(delta)
                if distance < 0.1: distance = 0.1
                
                # Repulsive force (pushes nodes apart)
                repulsive_force = k_repel / distance
                displacements[u] += (delta / distance) * repulsive_force
                displacements[v] -= (delta / distance) * repulsive_force
                
        # 2. Attractive forces along edges
        for node, data in node_data.items():
            if data['parent'] is not None and data['parent'] in positions:
                parent = data['parent']
                pos_node, pos_parent = np.array(positions[node]), np.array(positions[parent])
                delta = pos_node - pos_parent
                distance = np.linalg.norm(delta)
                if distance < 0.1: distance = 0.1

                # Ideal distance for the spring from the node's data
                ideal_length = data['distance'] * base_spacing
                
                # Attractive force (pulls connected nodes together)
                attractive_force = k_attract * (distance - ideal_length)
                displacements[node] -= (delta / distance) * attractive_force
                displacements[parent] += (delta / distance) * attractive_force
                
        # 3. Apply calculated displacements
        for node in nodes:
            if node != 'start': # Keep the root node fixed
                disp = displacements[node]
                # Dampen movement to prevent wild oscillations
                movement = np.linalg.norm(disp)
                if movement > 1.0:
                    disp = disp / movement
                positions[node] = (positions[node][0] + disp[0], positions[node][1] + disp[1])
                
    return positions

def rescale_positions(positions, target_radius=10.0):
    non_root_positions = [(x, y) for node, (x, y) in positions.items() if (x, y) != (0, 0)]
    if not non_root_positions: return positions
    max_dist = max(np.hypot(x, y) for x, y in non_root_positions)
    if max_dist == 0: return positions
    scale = target_radius / max_dist
    return {node: (x * scale, y * scale) for node, (x, y) in positions.items()}

def generate_figure(node_data, clicked_nodes_list, focus_node="start", node_flash=None):
    clicked_nodes = set(clicked_nodes_list)
    positions = build_positions(node_data, focus_node=focus_node)
    positions = apply_force_directed_layout(positions, node_data)
    
    # Conditionally rescale positions only if the graph is too large
    target_radius = 10.0
    non_root_positions = [(x, y) for node, (x, y) in positions.items() if (x, y) != (0, 0)]
    
    if non_root_positions:
        current_max_radius = max(np.hypot(x, y) for x, y in non_root_positions)
        if current_max_radius > target_radius:
            scale_factor = target_radius / current_max_radius
            positions = {node: (x * scale_factor, y * scale_factor) for node, (x, y) in positions.items()}

    xs, ys, labels, colors = [], [], [], []
    edge_xs, edge_ys = [], []
    edge_colors = []
    sizes = []

    root_size = max(80, 120 - 2 * (len(positions) - 1))
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
                if node in clicked_nodes:
                    edge_colors.append('rgba(2,171,19,0.35)')
                else:
                    edge_colors.append('#888')
        elif node != "start":
            label += f" ({breadth})"
        # Root node size gently decreases as more nodes are added, but never below 80
        if node == "start":
            size = root_size
        else:
            size = 300 * breadth/3
        # Flash effect: if node matches node_flash, make it larger and/or different color
        if node_flash is not None and node == node_flash:
            size = size * 1.25
        sizes.append(size)
        labels.append(label)
        if node == "start":
            color = "black"
        elif node in clicked_nodes:
            color = "#02ab13"
        else:
            color = "#666666"
        if node_flash is not None and node == node_flash:
            color = "#ffe066"  # subtle yellow highlight
        colors.append(color)

    if len(positions) < 2:
        x_range, y_range = [-10, 10], [-10, 10]
    else:
        focus_pos = positions.get(focus_node, (0, 0))
        all_xs, all_ys = [p[0] for p in positions.values()], [p[1] for p in positions.values()]
        min_x, max_x, min_y, max_y = min(all_xs), max(all_xs), min(all_ys), max(all_ys)
        spread_x = max(focus_pos[0] - min_x, max_x - focus_pos[0])
        spread_y = max(focus_pos[1] - min_y, max_y - focus_pos[1])
        spread = max(spread_x, spread_y) * 1.2 + 5
        x_range, y_range = [focus_pos[0] - spread, focus_pos[0] + spread], [focus_pos[1] - spread, focus_pos[1] + spread]

    edge_traces = []
    for i in range(0, len(edge_xs), 3):
        color = edge_colors[i//3] if i//3 < len(edge_colors) else '#888'
        edge_traces.append(go.Scatter(x=edge_xs[i:i+2], y=edge_ys[i:i+2], mode="lines", line=dict(width=3, color=color), hoverinfo="none", showlegend=False))

    node_trace = go.Scatter(x=xs, y=ys, mode="markers+text", text=labels, textposition="top center", textfont=dict(color='#c0c0c0', size=12),
        marker=dict(size=sizes, color=colors, opacity=1, line=dict(width=2, color='#444444')),
        customdata=list(positions.keys()), hoverinfo="text", selected=dict(marker=dict(opacity=1)), unselected=dict(marker=dict(opacity=1)))

    layout = go.Layout(clickmode="event+select", xaxis=dict(visible=False, range=x_range), yaxis=dict(visible=False, range=y_range),
        margin=dict(l=20, r=20, t=40, b=20), height=700, transition={'duration': 500, 'easing': 'cubic-in-out'},
        showlegend=False, plot_bgcolor='#1a1a1a', paper_bgcolor='#1a1a1a')

    return go.Figure(data=edge_traces + [node_trace], layout=layout)

# === Dash Layout ===
initial_state = get_initial_state()
app.layout = html.Div([
    html.H2("ELIE (Explain Like I'm an Expert)", style={"textAlign": "left", "color": "#c0c0c0", "marginTop": 0, "paddingTop": "20px", "paddingBottom": "10px"}),
    dcc.Store(id='app-state-store', data=initial_state),
    dcc.Store(id='input-overlay-visible'),
    dcc.Store(id='graph-key', data=0),
    dcc.Store(id='input-flash', data=False),
    dcc.Store(id='node-flash', data=None),
    html.Div(id="loading-output", style={"display": "none"}),
    html.Div([
        html.Div([
            html.Div(
                id="graph-container",
                children=[
                    dcc.Graph(
                        id={"type": "graph", "key": 0},
                        figure=generate_figure(initial_state['node_data'], initial_state['clicked_nodes_list'], initial_state['last_clicked'], node_flash=None),
                        relayoutData=None,
                        style={"flex": "3 1 0%", "position": "relative", "zIndex": 1}
                    )
                ]
            ),
            html.Div(html.Div([
                    dcc.Input(id="start-input", type="text", placeholder="Enter root concept...", debounce=True, n_submit=0, style={
                        "padding": "12px 45px 12px 28px", "fontSize": "1.18em", "borderRadius": "9px", "backgroundColor": "#333333",
                        "border": "1.5px solid #888888", "color": "#e0e0e0", "boxShadow": "0 2px 8px rgba(0,0,0,0.07)",
                        "outline": "none", "width": "100%", "textAlign": "center", "boxSizing": "border-box"}),
                    html.Button('↑', id='submit-btn', n_clicks=0, style={
                        "position": "absolute", "right": "8px", "top": "50%", "transform": "translateY(-50%)", "width": "32px", "height": "32px",
                        "borderRadius": "50%", "border": "none", "backgroundColor": "#555", "color": "#e0e0e0", "fontSize": "20px",
                        "cursor": "pointer", "display": "flex", "alignItems": "center", "justifyContent": "center", "paddingBottom": "4px"})
                ], style={"position": "relative", "width": "340px"}),
                id="centered-input-overlay",
                style={"position": "absolute", "left": "50%", "top": "55%", "transform": "translate(-50%, -50%)", "zIndex": 10, "pointerEvents": "auto", "transition": "opacity 0.3s ease, transform 0.3s ease"}
            ),
        ], style={"flex": "3 1 0%", "position": "relative", "minHeight": "700px", "border": "3px solid silver", "borderRadius": "15px", "overflow": "hidden"}),
        html.Div([
            html.Div([
                html.Button("Reset", id="reset-term-btn", n_clicks=0, style={"padding": "8px 16px", "fontSize": "0.95em", "borderRadius": "5px", "backgroundColor": "#333333", "border": "1px solid #555555", "color": "#c0c0c0", "cursor": "pointer", "transition": "background 0.2s, color 0.2s"}),
                html.Button("Save", id="save-btn", n_clicks=0, style={"padding": "8px 16px", "fontSize": "0.95em", "borderRadius": "5px", "backgroundColor": "#333333", "border": "1px solid #555555", "color": "#c0c0c0", "cursor": "pointer", "transition": "background 0.2s, color 0.2s"}),
                dcc.Download(id="download-graph"),
                dcc.Upload(id="upload-graph", children=html.Button("Load", style={"padding": "8px 16px", "fontSize": "0.95em", "borderRadius": "5px", "backgroundColor": "#333333", "border": "1px solid #555555", "color": "#c0c0c0", "cursor": "pointer", "transition": "background 0.2s, color 0.2s"}), multiple=False),
            ], style={"marginBottom": "16px", "display": "flex", "gap": "10px", "justifyContent": "center"}),
            html.Div(id="info-box", children=[html.H4("Welcome to ELIE!", style={"color": "#c0c0c0"}), dcc.Markdown(initial_state['explanation_paragraph'])], style={"border": "1px solid #555555", "padding": "15px", "backgroundColor": "#2a2a2a", "color": "#c0c0c0", "borderRadius": "8px", "flex": "1 1 0%", "maxWidth": "350px", "minWidth": "220px", "marginTop": "0px"})
        ], style={"display": "flex", "flexDirection": "column", "alignItems": "stretch", "flex": "1 1 0%"})
    ], style={"display": "flex", "flexDirection": "row", "alignItems": "flex-start", "flexGrow": 1, "gap": "40px"}),
], style={'backgroundColor': '#1a1a1a', 'minHeight': '100vh', "padding": "0 40px", "boxSizing": "border-box", "display": "flex", "flexDirection": "column"})

@app.callback(
    [Output("graph-container", "children"), Output("info-box", "children"), Output("upload-graph", "contents"),
     Output("input-overlay-visible", "data"), Output("start-input", "value"), Output("app-state-store", "data"),
     Output("graph-key", "data"), Output("input-flash", "data"), Output("node-flash", "data")],
    [Input({'type': 'graph', 'key': ALL}, 'clickData'), Input("start-input", "n_submit"), Input("upload-graph", "contents"),
     Input("reset-term-btn", "n_clicks"), Input("submit-btn", "n_clicks")],
    [State("start-input", "value"), State("app-state-store", "data"), State("graph-key", "data")]
)
def handle_interaction(clickData_list, input_submit, upload_contents, reset_clicks, submit_clicks, user_input, state, graph_key):
    ctx = dash.callback_context
    trigger_id = ctx.triggered[0]["prop_id"].split(".")[0] if ctx.triggered else None

    # Extract the first non-None clickData from the list
    clickData = next((cd for cd in clickData_list if cd), None)

    def make_graph(fig, key):
        print(f"Rendering graph with id=graph-{key}")
        return dcc.Graph(id={"type": "graph", "key": key}, figure=fig, relayoutData=None, style={"flex": "3 1 0%", "position": "relative", "zIndex": 1})

    def autoscale_figure(fig):
        # Set autorange for xaxis and yaxis in the layout
        fig.update_layout(xaxis={"autorange": True}, yaxis={"autorange": True})
        return fig

    if trigger_id == "reset-term-btn":
        print("Reset button clicked, forcing graph re-render with new key.")
        new_state = get_initial_state()
        info = [html.H4("Welcome to ELIE!", style={"color": "#c0c0c0"}), dcc.Markdown(new_state['explanation_paragraph'])]
        fig = generate_figure(new_state['node_data'], new_state['clicked_nodes_list'], new_state['last_clicked'], node_flash=None)
        fig = autoscale_figure(fig)
        new_key = graph_key + 1
        return make_graph(fig, new_key), info, None, True, "", new_state, new_key, False, None

    if trigger_id == "upload-graph" and upload_contents is not None:
        print("Graph loaded from file, forcing graph re-render with new key.")
        _, content_string = upload_contents.split(',')
        data = json.loads(base64.b64decode(content_string).decode('utf-8'))
        new_state = {
            "node_data": data.get("node_data", {}),
            "clicked_nodes_list": data.get("clicked_nodes_list", []),
            "unclicked_nodes": data.get("unclicked_nodes", []),
            "explanation_paragraph": data.get("explanation", HOW_IT_WORKS_MD),
            "last_clicked": "start"
        }
        recompute_all_distances(new_state['node_data'])
        term = new_state['node_data']['start'].get('label', 'start')
        info = [html.H4(f"About {term}", style={"color": "#c0c0c0"}), dcc.Markdown(new_state['explanation_paragraph'])]
        fig = generate_figure(new_state['node_data'], new_state['clicked_nodes_list'], new_state['last_clicked'], node_flash=None)
        fig = autoscale_figure(fig)
        new_key = graph_key + 1
        return make_graph(fig, new_key), info, None, False, dash.no_update, new_state, new_key, False, None

    if (trigger_id == "start-input" or trigger_id == "submit-btn") and user_input:
        print(f"Root concept submitted: {user_input}. Forcing graph re-render with new key.")
        term = user_input.strip()
        parsed_terms = None
        while True: # Retry loop until successful
            try:
                llm_response = call_gemini_llm(build_starter_prompt(term))
                parsed = parse_terms(llm_response, num_terms=4)
                if parsed: # Check if parsing was successful
                    parsed_terms = parsed
                    break
            except Exception as e:
                print(f"LLM call/parsing failed. Retrying... Error: {e}")
            time.sleep(1)
        
        if not parsed_terms:
            print("Failed to parse terms from LLM. No graph update.")
            return [dash.no_update] * 6 + [graph_key, False, None]

        node_data = {"start": {"parent": None, "distance": 0.0, "label": term}}
        for child_term, props in parsed_terms.items():
            node_data[child_term] = {"parent": "start", "distance": props["distance"], "raw_distance": props["distance"], "breadth": props["breadth"], "raw_breadth": props["breadth"]}
        
        recompute_all_distances(node_data)
        new_state = {
            "node_data": node_data,
            "clicked_nodes_list": [],
            "unclicked_nodes": [k for k in node_data.keys() if k != "start"],
            "last_clicked": "start"
        }
        new_state["explanation_paragraph"] = call_gemini_llm(build_final_prompt(term, new_state['clicked_nodes_list'], new_state['unclicked_nodes']))
        
        info = [html.H4(f"About {term}", style={"color": "#c0c0c0"}), dcc.Markdown(new_state['explanation_paragraph'])]
        fig = generate_figure(new_state['node_data'], new_state['clicked_nodes_list'], new_state['last_clicked'], node_flash=None)
        fig = autoscale_figure(fig)
        new_key = graph_key + 1
        return make_graph(fig, new_key), info, dash.no_update, False, dash.no_update, new_state, new_key, False, None

    if clickData and "points" in clickData:
        clicked = clickData["points"][0].get("customdata")
        if not clicked or (clicked == "start" and clicked in state['clicked_nodes_list']):
            print("Graph click ignored (clicked start or already clicked). No graph update.")
            return [dash.no_update] * 6 + [graph_key, False, None]
        
        new_state = state.copy()
        if clicked not in new_state['clicked_nodes_list']:
            print(f"Node '{clicked}' clicked, forcing graph re-render with new key.")
            new_state['clicked_nodes_list'].append(clicked)
            if clicked in new_state['unclicked_nodes']:
                new_state['unclicked_nodes'].remove(clicked)

            initial_term = new_state['node_data']["start"].get("label", "start")
            
            parsed_terms = None
            while True: # Retry loop until successful
                try:
                    further_prompt = build_further_prompt(initial_term, new_state['unclicked_nodes'], new_state['clicked_nodes_list'])
                    llm_response = call_gemini_llm(further_prompt)
                    parsed = parse_terms(llm_response, num_terms=3)
                    if parsed: # Check if parsing was successful
                        parsed_terms = parsed
                        break
                except Exception as e:
                    print(f"LLM call/parsing failed. Retrying... Error: {e}")
                time.sleep(1)

            if not parsed_terms:
                print("Failed to parse further terms from LLM. No graph update.")
                return [dash.no_update] * 6 + [graph_key, False, None]

            for child_term, props in parsed_terms.items():
                if child_term not in new_state['node_data']:
                    new_state['node_data'][child_term] = {"parent": clicked, "distance": props["distance"], "raw_distance": props["distance"], "breadth": props["breadth"], "raw_breadth": props["breadth"]}
                    if child_term not in new_state['unclicked_nodes'] and child_term not in new_state['clicked_nodes_list']:
                        new_state['unclicked_nodes'].append(child_term)

            recompute_all_distances(new_state['node_data'])
            new_state["explanation_paragraph"] = call_gemini_llm(build_final_prompt(initial_term, new_state['unclicked_nodes'], new_state['clicked_nodes_list']))
        else:
            print(f"Node '{clicked}' already clicked. No graph update.")
        new_state['last_clicked'] = clicked
        term = new_state['node_data']['start'].get('label', 'start')
        info = [html.H4(f"About {term}", style={"color": "#c0c0c0"}), dcc.Markdown(new_state['explanation_paragraph'])]
        fig = generate_figure(new_state['node_data'], new_state['clicked_nodes_list'], new_state['last_clicked'], node_flash=clicked)
        fig = autoscale_figure(fig)
        new_key = graph_key + 1
        return make_graph(fig, new_key), info, dash.no_update, False, dash.no_update, new_state, new_key, False, clicked

    print("No update triggered. No graph update.")
    return [dash.no_update] * 6 + [graph_key, False, None]

@app.callback(
    Output("download-graph", "data"),
    Input("save-btn", "n_clicks"),
    State("app-state-store", "data"),
    prevent_initial_call=True
)
def save_graph(n_clicks, state):
    if n_clicks:
        export_data = {
            "node_data": state['node_data'],
            "clicked_nodes_list": state['clicked_nodes_list'],
            "unclicked_nodes": state['unclicked_nodes'],
            "explanation": state['explanation_paragraph']
        }
        return dict(content=json.dumps(export_data, indent=2), filename="elie_graph.json")
    return dash.no_update

@app.callback(
    Output("centered-input-overlay", "style"),
    Input("input-overlay-visible", "data"),
)
def toggle_overlay(visible):
    base_style = {"position": "absolute", "left": "50%", "top": "55%", "zIndex": 10, "transition": "opacity 0.3s ease, transform 0.3s ease"}
    if visible:
        return {**base_style, "transform": "translate(-50%, -50%)", "opacity": 1, "pointerEvents": "auto"}
    else:
        return {**base_style, "transform": "translate(-50%, -65%)", "opacity": 0, "pointerEvents": "none"}

# Flash reset callbacks
@app.callback(
    Output('input-flash', 'data', allow_duplicate=True),
    Input('input-flash', 'data'),
    prevent_initial_call=True
)
def reset_input_flash(flash):
    if flash:
        time.sleep(0.3)
        return False
    return dash.no_update

@app.callback(
    Output('node-flash', 'data', allow_duplicate=True),
    Input('node-flash', 'data'),
    prevent_initial_call=True
)
def reset_node_flash(node):
    if node is not None:
        time.sleep(0.3)
        return None
    return dash.no_update

# Input style callback
@app.callback(
    Output('start-input', 'style'),
    Input('input-flash', 'data'),
)
def style_input_box(flash):
    base_style = {
        "padding": "12px 45px 12px 28px", "fontSize": "1.18em", "borderRadius": "9px", "backgroundColor": "#333333",
        "border": "1.5px solid #888888", "color": "#e0e0e0", "boxShadow": "0 2px 8px rgba(0,0,0,0.07)",
        "outline": "none", "width": "100%", "textAlign": "center", "boxSizing": "border-box"
    }
    if flash:
        base_style["border"] = "2.5px solid #02ab13"
        base_style["boxShadow"] = "0 0 12px #02ab13"
    return base_style

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8050))
    app.run(debug=True, port=port)
    app.run(debug=True, host="0.0.0.0", port=port)
