"""
Configuration module for ELIE app
Contains constants, styling, and app settings
"""

# === APP METADATA ===
APP_TITLE = "ELIE (Explain Like I'm an Expert)"
DEFAULT_PORT = 8050

# === GRAPH SETTINGS ===
GRAPH_CONFIG = {
    "base_spacing": 5.0,
    "target_radius": 10.0,
    "force_layout": {
        "iterations": 100,
        "k_attract": 0.02,
        "k_repel": 0.2
    },
    "root_size_base": 120,
    "root_size_min": 80,
    "node_size_base": 50,
    "node_size_multiplier": 30
}

# === LLM SETTINGS ===
LLM_CONFIG = {
    "starter_terms": 4,
    "further_terms": 3,
    "suggestion_terms": 4,
    "retry_delay": 1.0
}

# === ANIMATION SETTINGS ===
ANIMATION_CONFIG = {
    "toggle_duration": 700,
    "reload_timer_interval": 500,  # Increased from 100ms to 500ms for more reliable LLM calls
    "submit_flash_duration": 1200
}

# === COLOR SCHEME ===
COLORS = {
    "background": "#1a1a1a",
    "secondary_bg": "#2a2a2a",
    "text_primary": "#c0c0c0",
    "text_secondary": "#e0e0e0",
    "accent_green": "#02ab13",
    "accent_green_dark": "#047015",
    "accent_green_glow": "#00ff00",
    "neutral_gray": "#666666",
    "neutral_dark": "#333333",
    "neutral_medium": "#555555",
    "neutral_light": "#888888",
    "border_color": "#555555",
    "black": "black"
}

# === BUTTON STYLES ===
BUTTON_STYLES = {
    "base": {
        "border": "none",
        "cursor": "pointer",
        "transition": "background 0.2s, color 0.2s"
    },
    "control": {
        "padding": "8px 16px",
        "fontSize": "0.95em",
        "borderRadius": "5px",
        "backgroundColor": COLORS["neutral_dark"],
        "border": f"1px solid {COLORS['border_color']}",
        "color": COLORS["text_primary"]
    },
    "submit": {
        "position": "absolute",
        "right": "0.5em",
        "top": 0,
        "bottom": 0,
        "margin": "auto",
        "width": "1.7em",
        "height": "1.7em",
        "borderRadius": "50%",
        "backgroundColor": COLORS["neutral_medium"],
        "color": COLORS["text_secondary"],
        "fontSize": "1.25em",
        "display": "flex",
        "alignItems": "center",
        "justifyContent": "center",
        "transition": "transform 0.2s ease"
    },
    "suggested": {
        "display": "inline-block",
        "background": "#232a3a",
        "color": COLORS["accent_green"],
        "borderRadius": "18px",
        "padding": "7px 18px",
        "margin": "0 7px 7px 0",
        "fontWeight": 600,
        "fontSize": "1.05em",
        "boxShadow": "0 2px 8px rgba(2,171,19,0.07)",
        "border": f"1.5px solid {COLORS['accent_green']}"
    }
}

# === INPUT STYLES ===
INPUT_STYLES = {
    "main": {
        "padding": "12px 45px 12px 28px",
        "fontSize": "1.18em",
        "borderRadius": "9px",
        "backgroundColor": COLORS["neutral_dark"],
        "border": f"1.5px solid {COLORS['neutral_light']}",
        "color": COLORS["text_secondary"],
        "boxShadow": "0 2px 8px rgba(0,0,0,0.07)",
        "outline": "none",
        "width": "100%",
        "textAlign": "center",
        "boxSizing": "border-box"
    }
}

# === LAYOUT STYLES ===
LAYOUT_STYLES = {
    "main_container": {
        "backgroundColor": COLORS["background"],
        "minHeight": "100vh",
        "padding": "0 40px",
        "boxSizing": "border-box",
        "display": "flex",
        "flexDirection": "column"
    },
    "flex_row": {
        "display": "flex",
        "flexDirection": "row",
        "alignItems": "flex-start",
        "flexGrow": 1,
        "gap": "40px"
    },
    "graph_section": {
        "flex": "3 1 0%",
        "position": "relative",
        "minHeight": "700px",
        "borderRadius": "15px",
        "overflow": "hidden"
    },
    "sidebar": {
        "display": "flex",
        "flexDirection": "column",
        "alignItems": "stretch",
        "flex": "1 1 0%"
    },
    "info_box": {
        "border": f"1px solid {COLORS['border_color']}",
        "padding": "15px",
        "backgroundColor": COLORS["secondary_bg"],
        "color": COLORS["text_primary"],
        "borderRadius": "8px",
        "flex": "1 1 0%",
        "width": "350px",  # Set fixed width
        "maxWidth": "350px",
        "minWidth": "350px",  # Ensure consistent width
        "marginTop": "0px",
        "boxSizing": "border-box"  # Include padding and border in width calculation
    }
}

# === GRAPH COMPONENT STYLES ===
GRAPH_STYLES = {
    "container": {
        "flex": "3 1 0%",
        "position": "relative",
        "zIndex": 1
    },
    "config": {
        "displayModeBar": False
    }
}

# === OVERLAY STYLES ===
OVERLAY_STYLES = {
    "input_overlay": {
        "position": "absolute",
        "left": "50%",
        "top": "55%",  # Changed from 55% to 50% for true center
        "transform": "translate(-50%, -50%)",  # Added transform for perfect centering
        "zIndex": 10,
        "transition": "opacity 0.3s ease, transform 0.3s ease",
        "width": "100%",
        "display": "flex",
        "justifyContent": "center",
        "alignItems": "center"
    },
    "input_container": {
        "position": "relative",
        "width": "21rem",  # Changed from fixed pixels to rem
        "display": "flex",
        "alignItems": "center"
    }
}

# === CONTROL BUTTON ICONS ===
ICONS = {
    "reload": "\u21bb",
    "toggle": "\U0001F4DA",  # 📚
    "submit": "↑"
}

# === CSS INJECTION ===
CSS_STYLES = """
html, body { margin: 0; padding: 0; height: 100%; width: 100%; background-color: #1a1a1a; }
#_dash-root-content { height: 100%; }
@keyframes spin { 
    100% { transform: rotate(360deg); } 
}
.spin-animation {
    animation: spin 1s linear infinite;
    transform-origin: center;
    display: flex;
    align-items: center;
    justify-content: center;
}
.toggle-btn:hover {
    transform: scale(1.15);
}
.reload-btn:hover {
    transform: scale(1.15);
}
.submit-btn:hover {
    transform: scale(1.15);
}
.reload-btn:active {
    transform: scale(0.95);
}
.toggle-btn:active {
    transform: scale(0.95);
}
.submit-btn:active {
    transform: scale(0.95);
}
"""

# === DEFAULT CONTENT ===
HOW_IT_WORKS_MD = """## How It Works

1. **Pick a topic:** Type in something you want to learn—say, "quaternions".

2. **Get a baseline:** ELIE shows you an initial explanation and a web of related concepts (e.g. "complex numbers", "rotation", "linear algebra").

3. **Click what you do not know:** Select any unfamiliar node—e.g. "linear algebra"—and ELIE refines the explanation.

4. **Iterate to expertise:** Keep choosing unknown concepts; the map updates and the explanation sharpens until it's perfectly pitched to your expertise.
"""

# === HTML TEMPLATE ===
HTML_TEMPLATE = f"""
<!DOCTYPE html>
<html>
    <head>
        {{%metas%}}
        <title>{{%title%}}</title>
        {{%favicon%}}
        {{%css%}}
        <style>
            {CSS_STYLES}
        </style>
    </head>
    <body>
        {{%app_entry%}}
        <footer>
            {{%config%}}
            {{%scripts%}}
            {{%renderer%}}
        </footer>
    </body>
</html>
""" 