"""
Graph Management module for ELIE app
Handles graph layout, positioning, visualization, and figure generation
"""

import numpy as np
import plotly.graph_objs as go
from config import GRAPH_CONFIG, COLORS


class GraphManager:
    """Manages graph layout, positioning, and visualization"""
    
    @staticmethod
    def build_node_positions(node_data, focus_node="start"):
        """Build initial positions for nodes using tree-based layout"""
        base_spacing = GRAPH_CONFIG["base_spacing"]
        positions = {}
        focus_path = []
        
        # Build focus path for weighted layout
        curr = focus_node
        while curr and curr in node_data:
            focus_path.append(curr)
            curr = node_data[curr].get("parent")
        focus_path.reverse()

        def dfs_layout(node, depth=0, angle=0.0, spread=np.pi * 2):
            """Depth-first search layout with focus weighting"""
            if node in positions:
                return
                
            if node == "start":
                x, y = 0, 0
            else:
                parent = node_data[node]["parent"]
                dist = node_data[node]["distance"]
                px, py = positions.get(parent, (0, 0))
                r = base_spacing * dist
                x, y = px + r * np.cos(angle), py + r * np.sin(angle)
            
            positions[node] = (x, y)

            children = [k for k, v in node_data.items() if v["parent"] == node]
            if not children:
                return

            # Determine next focus node for weighting
            next_focus_node = None
            if node in focus_path:
                idx = focus_path.index(node)
                if idx + 1 < len(focus_path):
                    next_focus_node = focus_path[idx + 1]

            # Weight children (focus path gets more space)
            weights = [3.0 if child == next_focus_node else 1.0 for child in children]
            total_weight = sum(weights)
            
            cursor = angle - spread / 2.0
            for i, child in enumerate(children):
                child_spread = spread * (weights[i] / total_weight)
                child_angle = cursor + child_spread / 2.0
                dfs_layout(child, depth + 1, child_angle, child_spread)
                cursor += child_spread
        
        dfs_layout("start")
        return positions
    
    @staticmethod
    def apply_force_directed_layout(positions, node_data):
        """Apply force-directed layout optimization to positions"""
        config = GRAPH_CONFIG["force_layout"]
        iterations = config["iterations"]
        k_attract = config["k_attract"]
        k_repel = config["k_repel"]
        base_spacing = GRAPH_CONFIG["base_spacing"]
        
        nodes = list(positions.keys())
        
        # Run simulation for specified iterations
        for _ in range(iterations):
            displacements = {node: np.array([0.0, 0.0]) for node in nodes}
            
            # 1. Repulsive forces between all pairs of nodes
            for i in range(len(nodes)):
                for j in range(i + 1, len(nodes)):
                    u, v = nodes[i], nodes[j]
                    pos_u, pos_v = np.array(positions[u]), np.array(positions[v])
                    delta = pos_u - pos_v
                    distance = np.linalg.norm(delta)
                    if distance < 0.1:
                        distance = 0.1
                    
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
                    if distance < 0.1:
                        distance = 0.1

                    # Ideal distance for the spring from the node's data
                    ideal_length = data['distance'] * base_spacing
                    
                    # Attractive force (pulls connected nodes together)
                    attractive_force = k_attract * (distance - ideal_length)
                    displacements[node] -= (delta / distance) * attractive_force
                    displacements[parent] += (delta / distance) * attractive_force
                    
            # 3. Apply calculated displacements
            for node in nodes:
                if node != 'start':  # Keep the root node fixed
                    disp = displacements[node]
                    # Dampen movement to prevent wild oscillations
                    movement = np.linalg.norm(disp)
                    if movement > 1.0:
                        disp = disp / movement
                    positions[node] = (positions[node][0] + disp[0], positions[node][1] + disp[1])
                    
        return positions
    
    @staticmethod
    def rescale_positions_if_needed(positions):
        """Conditionally rescale positions only if the graph is too large"""
        target_radius = GRAPH_CONFIG["target_radius"]
        non_root_positions = [(x, y) for node, (x, y) in positions.items() if (x, y) != (0, 0)]
        
        if non_root_positions:
            current_max_radius = max(np.hypot(x, y) for x, y in non_root_positions)
            if current_max_radius > target_radius:
                scale_factor = target_radius / current_max_radius
                positions = {node: (x * scale_factor, y * scale_factor) for node, (x, y) in positions.items()}
        
        return positions
    
    @staticmethod
    def calculate_node_visual_properties(node_data, positions, clicked_nodes_list, last_clicked, node_flash):
        """Calculate visual properties for nodes (size, color, labels)"""
        clicked_nodes = set(clicked_nodes_list)
        root_size_base = GRAPH_CONFIG["root_size_base"]
        root_size_min = GRAPH_CONFIG["root_size_min"]
        node_size_base = GRAPH_CONFIG["node_size_base"]
        node_size_multiplier = GRAPH_CONFIG["node_size_multiplier"]
        
        xs, ys, labels, colors, sizes, opacities = [], [], [], [], [], []
        
        # Root node size gently decreases as more nodes are added, but never below minimum
        root_size = max(root_size_min, root_size_base - 2 * (len(positions) - 1))
        
        for node, (x, y) in positions.items():
            xs.append(x)
            ys.append(y)
            
            # Node labels
            if node == "start" and "label" in node_data[node]:
                label = node_data[node]["label"]
            else:
                label = node
                
            # Node sizes
            if node == "start":
                size = root_size
            else:
                breadth = node_data[node].get("breadth", 1.0)
                size = node_size_base + node_size_multiplier * breadth
            
            # Flash effect: if node matches node_flash, make it larger
            if node_flash is not None and node == node_flash:
                size = size * 1.25
            
            sizes.append(size)
            labels.append(label)
            
            # Node coloring logic
            if node == "start":
                color = COLORS["black"]
            elif node == last_clicked:
                color = COLORS["white"]  # Light green for most recently clicked
            elif node in clicked_nodes:
                color = COLORS["wheat"]  # Dark green for previously clicked
            else:
                color = COLORS["accent_green"]
            
            colors.append(color)
            
            # Opacity logic: reduce opacity for other nodes when a node is clicked (not expanded)
            if last_clicked and last_clicked != "start" and last_clicked not in clicked_nodes_list:
                # A node was just clicked but not yet expanded - dim all nodes during loading
                opacity = 0.4  # Reduce opacity during loading
            else:
                opacity = 1.0  # Normal state - high opacity when not loading
            
            opacities.append(opacity)
        
        return xs, ys, labels, colors, sizes, opacities
    
    @staticmethod
    def calculate_edge_properties(node_data, positions, clicked_nodes_list, last_clicked=None):
        """Calculate visual properties for edges"""
        clicked_nodes = set(clicked_nodes_list)
        edge_xs, edge_ys, edge_colors = [], [], []
        
        for node, (x, y) in positions.items():
            parent = node_data[node]["parent"]
            if parent and parent in positions:
                px, py = positions[parent]
                edge_xs += [px, x, None]
                edge_ys += [py, y, None]
                
                # Determine edge color and opacity
                if node in clicked_nodes:
                    base_color = 'rgba(245,222,179,0.5)'
                else:
                    base_color = COLORS["accent_green_dark"]
                
                # Apply opacity reduction when a node is clicked (not expanded)
                if last_clicked and last_clicked != "start" and last_clicked not in clicked_nodes_list:
                    # A node was just clicked but not yet expanded - dim all edges during loading
                    if node in clicked_nodes:
                        edge_color = 'rgba(245,222,179,0.2)'  # Dimmed wheat color for loading
                    else:
                        # Convert hex color to rgba with reduced opacity for loading
                        if base_color == COLORS["accent_green_dark"]:
                            edge_color = 'rgba(4,112,21,0.16)'  # Dimmed accent_green_dark for loading
                        else:
                            edge_color = 'rgba(245,222,179,0.2)'  # Dimmed for loading
                else:
                    edge_color = base_color  # Normal state - full opacity when not loading
                
                edge_colors.append(edge_color)
        
        return edge_xs, edge_ys, edge_colors
    
    @staticmethod
    def calculate_view_range(positions, focus_node="start"):
        """Calculate appropriate view range for the graph"""
        if len(positions) < 2:
            return [-10, 10], [-10, 10]
        
        focus_pos = positions.get(focus_node, (0, 0))
        all_xs, all_ys = [p[0] for p in positions.values()], [p[1] for p in positions.values()]
        min_x, max_x, min_y, max_y = min(all_xs), max(all_xs), min(all_ys), max(all_ys)
        
        spread_x = max(focus_pos[0] - min_x, max_x - focus_pos[0])
        spread_y = max(focus_pos[1] - min_y, max_y - focus_pos[1])
        spread = max(spread_x, spread_y) * 1.2 + 5
        
        x_range = [focus_pos[0] - spread, focus_pos[0] + spread]
        y_range = [focus_pos[1] - spread, focus_pos[1] + spread]
        
        return x_range, y_range
    
    @staticmethod
    def create_edge_traces(edge_xs, edge_ys, edge_colors):
        """Create plotly traces for edges"""
        edge_traces = []
        for i in range(0, len(edge_xs), 3):
            color = edge_colors[i//3] if i//3 < len(edge_colors) else COLORS["neutral_light"]
            edge_traces.append(
                go.Scatter(
                    x=edge_xs[i:i+2],
                    y=edge_ys[i:i+2],
                    mode="lines",
                    line=dict(width=3, color=color),
                    hoverinfo="none",
                    showlegend=False
                )
            )
        return edge_traces
    
    @staticmethod
    def create_node_trace(xs, ys, labels, colors, sizes, opacities, positions):
        """Create plotly trace for nodes"""
        # Set customdata so that the start node is unclickable
        customdata = []
        for node in positions.keys():
            if node == "start":
                customdata.append(None)
            else:
                customdata.append(node)
        
        # Create text colors with opacity applied
        text_colors = []
        for opacity in opacities:
            if opacity < 1.0:
                # Convert text color to rgba with reduced opacity
                text_colors.append(f'rgba(192,192,192,{opacity})')  # text_primary with opacity
            else:
                text_colors.append(COLORS["text_primary"])
        
        return go.Scatter(
            x=xs, y=ys,
            mode="markers+text",
            text=labels,
            textposition="top center",
            textfont=dict(color=text_colors, size=12),
            # Add hover template with node name
            hovertemplate='<b>%{text}</b><extra></extra>',  # Show node name in bold
            hoverlabel=dict(
                bgcolor='rgba(0,0,0,0.8)',  # Semi-transparent dark background for contrast
                bordercolor='white',  # White border
                font=dict(color='white', size=16)  # White text, larger size
            ),
            marker=dict(
                size=sizes,
                color=colors,
                opacity=opacities,  # Use the opacity values
                line=dict(width=2, color='#444444')
            ),
            customdata=customdata,
            hoverinfo="text",
            selected=dict(marker=dict(opacity=1)),
            unselected=dict(marker=dict(opacity=1))
        )
    
    @staticmethod
    def create_layout(x_range, y_range):
        """Create plotly layout for the graph"""
        return go.Layout(
            clickmode="event+select",
            xaxis=dict(visible=False, range=x_range),
            yaxis=dict(visible=False, range=y_range),
            margin=dict(l=20, r=20, t=40, b=20),
            height=700,
            transition={'duration': 500, 'easing': 'cubic-in-out'},
            showlegend=False,
            plot_bgcolor=COLORS["background"],
            paper_bgcolor=COLORS["background"]
        )
    
    @staticmethod
    def generate_figure(node_data, clicked_nodes_list, focus_node="start", node_flash=None, last_clicked=None):
        """Generate complete plotly figure for the concept map"""
        # Use last item in clicked_nodes_list if last_clicked not provided
        if last_clicked is None and clicked_nodes_list:
            last_clicked = clicked_nodes_list[-1]
        
        # Calculate positions
        positions = GraphManager.build_node_positions(node_data, focus_node=focus_node)
        positions = GraphManager.apply_force_directed_layout(positions, node_data)
        positions = GraphManager.rescale_positions_if_needed(positions)
        
        # Calculate visual properties
        xs, ys, labels, colors, sizes, opacities = GraphManager.calculate_node_visual_properties(
            node_data, positions, clicked_nodes_list, last_clicked, node_flash
        )
        
        edge_xs, edge_ys, edge_colors = GraphManager.calculate_edge_properties(
            node_data, positions, clicked_nodes_list, last_clicked
        )
        
        x_range, y_range = GraphManager.calculate_view_range(positions, focus_node)
        
        # Create traces
        edge_traces = GraphManager.create_edge_traces(edge_xs, edge_ys, edge_colors)
        node_trace = GraphManager.create_node_trace(xs, ys, labels, colors, sizes, opacities, positions)
        layout = GraphManager.create_layout(x_range, y_range)
        
        # Create and return figure
        fig = go.Figure(data=edge_traces + [node_trace], layout=layout)
        return fig
    
    @staticmethod
    def autoscale_figure(fig):
        """Update figure to use autoscaled axes"""
        fig.update_layout(
            xaxis={"autorange": True},
            yaxis={"autorange": True}
        )
        return fig 