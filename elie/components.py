"""
UI Components module for ELIE app
Contains factory functions for creating reusable UI components
"""

from dash import dcc, html
from config import (
    APP_TITLE, COLORS, BUTTON_STYLES, INPUT_STYLES, LAYOUT_STYLES, 
    GRAPH_STYLES, OVERLAY_STYLES, ICONS, HOW_IT_WORKS_MD, ANIMATION_CONFIG
)


def create_app_header():
    """Create the main application header"""
    return html.H2(
        APP_TITLE,
        style={
            "textAlign": "left",
            "color": COLORS["text_primary"],
            "marginTop": 0,
            "paddingTop": "20px",
            "paddingBottom": "10px"
        }
    )


def create_data_stores(initial_state):
    """Create all dcc.Store components for app state management"""
    return [
        dcc.Store(id='app-state-store', data=initial_state),
        dcc.Store(id='input-overlay-visible'),
        dcc.Store(id='graph-key', data=0),
        dcc.Store(id='input-flash', data=False),
        dcc.Store(id='node-flash', data=None),
        dcc.Store(id='submit-btn-flash', data=False),
        dcc.Store(id='explanation-length-flag', data='short', storage_type='local'),
        dcc.Store(id='toggle-animating', data=False),
        dcc.Store(id='reload-spinning', data=False),
        dcc.Store(id='reload-triggered', data=False),
        dcc.Store(id='reload-last-click', data=0),  # Track last reload button click count
    ]


def create_timers():
    """Create dcc.Interval components for animations"""
    return [
        dcc.Interval(
            id='animation-timer',
            interval=ANIMATION_CONFIG["toggle_duration"],
            n_intervals=0,
            disabled=True
        ),
        dcc.Interval(
            id='reload-timer',
            interval=ANIMATION_CONFIG["reload_timer_interval"],
            n_intervals=0,
            disabled=True,
            max_intervals=1  # Only fire once per enable cycle
        ),
    ]


def create_toggle_button(length_flag="short", animating=False):
    """Create the toggle explanation length button"""
    icon = ICONS["toggle"]
    
    if length_flag == "short":
        bg = "none"
        color = COLORS["text_primary"]
    else:
        bg = COLORS["accent_green"]
        color = "#fff"
    
    box_shadow = "0 0 0 0 #00ff00"  # default no glow
    if animating:
        box_shadow = f"0 0 24px 8px {COLORS['accent_green_glow']}"
    
    return html.Button(
        icon,
        id="toggle-explanation-btn",
        title="Toggle short/long explanation",
        style={
            **BUTTON_STYLES["base"],
            "background": bg,
            "color": color,
            "fontSize": "2.1em",
            "padding": "0 24px",
            "verticalAlign": "middle",
            "float": "right",
            "minWidth": "64px",
            "height": "48px",
            "borderRadius": "12px",
            "transition": "background 0.2s, color 0.2s, box-shadow 0.7s cubic-bezier(.4,2,.6,1)",
            "boxShadow": box_shadow
        }
    )


def create_reload_button(spinning=False):
    """Create the reload explanation button"""
    style = {
        **BUTTON_STYLES["base"],
        "background": "none",
        "color": COLORS["text_primary"],
        "fontSize": "2.1em",
        "marginRight": "16px",
        "padding": "0 24px 0 0",
        "verticalAlign": "middle",
        "minWidth": "64px",
        "height": "48px",
        "transition": "transform 0.2s",
        "transformOrigin": "center",
    }
    
    # Use CSS class for spinning animation instead of inline animation
    class_name = "spin-animation" if spinning else ""
    
    return html.Button(
        ICONS["reload"],
        id="reload-explanation-btn",
        title="Reload explanation",
        n_clicks=0,
        style=style,
        className=class_name
    )


def create_submit_button(flash=False):
    """Create the submit button for the input field"""
    style = {
        **BUTTON_STYLES["base"],
        **BUTTON_STYLES["submit"],
        "transition": f"box-shadow {ANIMATION_CONFIG['submit_flash_duration'] / 1000}s, background {ANIMATION_CONFIG['submit_flash_duration'] / 1000}s, color {ANIMATION_CONFIG['submit_flash_duration'] / 1000}s"
    }
    
    if flash:
        style.update({
            "backgroundColor": "#fff",
            "color": COLORS["accent_green"],
            "boxShadow": "0 0 24px 8px #f0fff0"
        })
    
    return html.Button(
        ICONS["submit"],
        id='submit-btn',
        n_clicks=0,
        style=style
    )


def create_control_button(text, button_id, n_clicks=0):
    """Create a standard control button (Reset, Save, Load)"""
    return html.Button(
        text,
        id=button_id,
        n_clicks=n_clicks,
        style={
            **BUTTON_STYLES["base"],
            **BUTTON_STYLES["control"]
        }
    )


def create_suggested_term_button(term):
    """Create a suggested term button"""
    return html.Button(
        term,
        id={"type": "suggested-term", "term": term},
        n_clicks=0,
        style={
            **BUTTON_STYLES["base"],
            **BUTTON_STYLES["suggested"],
            "transition": "background 0.2s, color 0.2s"
        }
    )


def create_input_field():
    """Create the main input field for entering concepts"""
    return dcc.Input(
        id="start-input",
        type="text",
        placeholder="Enter root concept...",
        debounce=True,
        n_submit=0,
        style=INPUT_STYLES["main"]
    )


def create_graph_component(figure, graph_key):
    """Create a graph component with the given figure and key"""
    return dcc.Graph(
        id={"type": "graph", "key": graph_key},
        figure=figure,
        relayoutData=None,
        style=GRAPH_STYLES["container"],
        config=GRAPH_STYLES["config"]
    )


def create_info_box_content(term=None, explanation="", length_flag="short", animating=False, spinning=False):
    """Create the content for the info box"""
    if term is None:
        # Return welcome message for initial state
        return [
            html.H4("Welcome to ELIE!", style={"color": COLORS["text_primary"]}),
            dcc.Markdown(explanation or HOW_IT_WORKS_MD)
        ]
    
    # Return info box with controls
    return [
        html.Div([
            create_reload_button(spinning=spinning),
            html.H4(
                f"About {term}",
                style={
                    "color": COLORS["text_primary"],
                    "margin": 0,
                    "marginLeft": "10px",
                    "fontWeight": 700,
                    "fontSize": "1.2em",
                    "verticalAlign": "middle"
                }
            ),
            create_toggle_button(length_flag, animating=animating)
        ], style={
            "display": "flex",
            "alignItems": "center",
            "gap": "8px",
            "marginBottom": "10px",
            "width": "100%"
        }),
        dcc.Markdown(explanation)
    ]


def create_suggested_concepts_section(suggestions=None):
    """Create the suggested concepts section"""
    if not suggestions:
        return ""
    
    return html.Div([
        html.Div(
            "You could now explore:",
            style={
                "color": COLORS["text_primary"],
                "fontSize": "1.30em",
                "marginBottom": "10px"
            }
        ),
        html.Div([
            create_suggested_term_button(term) for term in suggestions
        ], style={
            "display": "flex",
            "flexWrap": "wrap",
            "justifyContent": "center"
        })
    ], style={
        "position": "relative",
        "paddingBottom": "10px"
    })


def create_input_overlay():
    """Create the centered input overlay"""
    return html.Div(
        html.Div([
            create_input_field(),
            create_submit_button()
        ], style=OVERLAY_STYLES["input_container"]),
        id="centered-input-overlay",
        style=OVERLAY_STYLES["input_overlay"]
    )


def create_control_panel():
    """Create the control panel with Reset, Save, Load buttons"""
    return html.Div([
        create_control_button("Reset", "reset-term-btn"),
        create_control_button("Save", "save-btn"),
        dcc.Download(id="download-graph"),
        dcc.Upload(
            id="upload-graph",
            children=create_control_button("Load", "upload-load-btn"),
            multiple=False
        ),
    ], style={
        "marginBottom": "16px",
        "display": "flex",
        "gap": "10px",
        "justifyContent": "center"
    })


def create_info_box(content):
    """Create the info box container"""
    return html.Div(
        id="info-box",
        children=content,
        style=LAYOUT_STYLES["info_box"]
    )


def create_graph_container(graph_component):
    """Create the graph container section"""
    return html.Div([
        html.Div(
            id="graph-container",
            children=[graph_component]
        ),
        html.Div(
            id="suggested-concepts-container",
            style={"marginTop": "24px", "textAlign": "center"}
        ),
        create_input_overlay()
    ], style=LAYOUT_STYLES["graph_section"])


def create_sidebar(control_panel, info_box):
    """Create the sidebar section"""
    return html.Div([
        control_panel,
        info_box
    ], style=LAYOUT_STYLES["sidebar"])


def create_main_layout(graph_container, sidebar):
    """Create the main application layout"""
    return html.Div([
        create_app_header(),
        html.Div(id="loading-output", style={"display": "none"}),
        html.Div([
            graph_container,
            sidebar
        ], style=LAYOUT_STYLES["flex_row"])
    ], style=LAYOUT_STYLES["main_container"]) 