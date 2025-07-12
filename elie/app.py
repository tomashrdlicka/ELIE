"""
ELIE (Explain Like I'm an Expert) - Main Application
A modular Dash app for interactive concept learning with visual knowledge graphs
"""

import os
import dash

# Import modular components
from config import DEFAULT_PORT, HTML_TEMPLATE
from components import (
    create_data_stores, create_timers, create_control_panel, 
    create_info_box, create_graph_container, create_sidebar, 
    create_main_layout, create_graph_component, create_info_box_content
)
from state_manager import StateManager
from graph_manager import GraphManager
from callback_handlers import CallbackHandlers

# Initialize Dash app
app = dash.Dash(__name__, suppress_callback_exceptions=True)
server = app.server

# Set custom HTML template
app.index_string = HTML_TEMPLATE

def create_app_layout():
    """Create the complete application layout using modular components"""
    # Get initial state
    initial_state = StateManager.get_initial_state()
    
    # Create initial graph figure
    initial_figure = GraphManager.generate_figure(
        initial_state['node_data'],
        initial_state['clicked_nodes_list'],
        initial_state['last_clicked']
    )
    
    # Create initial graph component
    initial_graph = create_graph_component(initial_figure, 0)
    
    # Create layout sections
    data_stores = create_data_stores(initial_state)
    timers = create_timers()

    # Create UI sections
    graph_container = create_graph_container(initial_graph)
    control_panel = create_control_panel()
    
    # Create empty info box - content will be set by the UI callback
    info_box = create_info_box([])
    
    sidebar = create_sidebar(control_panel, info_box)
    
    # Combine all components
    layout_components = data_stores + timers + [
        create_main_layout(graph_container, sidebar)
    ]
    
    return layout_components

# Set app layout
app.layout = create_app_layout()

# Initialize callback handlers
callback_handlers = CallbackHandlers(app)

# Add remaining callback for submit button styling (missing from callback_handlers)
@app.callback(
    dash.Output('submit-btn', 'style'),
    dash.Input('submit-btn-flash', 'data'),
)
def style_submit_btn(flash):
    """Style submit button based on flash state"""
    from config import BUTTON_STYLES, COLORS, ANIMATION_CONFIG
    
    base_style = {
        **BUTTON_STYLES["base"],
        **BUTTON_STYLES["submit"],
        "transition": f"box-shadow {ANIMATION_CONFIG['submit_flash_duration'] / 1000}s, background {ANIMATION_CONFIG['submit_flash_duration'] / 1000}s, color {ANIMATION_CONFIG['submit_flash_duration'] / 1000}s"
    }
    
    if flash:
        base_style.update({
            "backgroundColor": "#fff",
            "color": COLORS["accent_green"],
            "boxShadow": "0 0 24px 8px #f0fff0"
        })
    
    return base_style

if __name__ == "__main__":
    port = int(os.getenv("PORT", DEFAULT_PORT))
    app.run(debug=False, host="0.0.0.0", port=port, dev_tools_ui=False, dev_tools_props_check=False)
