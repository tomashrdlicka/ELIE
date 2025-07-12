# ELIE - Modular Architecture Documentation

## Overview

ELIE (Explain Like I'm an Expert) has been refactored into a modular architecture for better maintainability, extensibility, and code organization. The original 965-line `app.py` has been reduced to 99 lines and split into 5 focused modules.

## Architecture Benefits

- **90% reduction** in main app file complexity
- **Clear separation of concerns** - each module has a single responsibility
- **Reusable components** - UI elements can be easily modified or extended
- **Centralized configuration** - all constants and styling in one place
- **Organized callbacks** - logical grouping of Dash callbacks
- **Easy to understand** - human-readable code structure
- **Simple to extend** - add new features without touching existing logic

## Module Structure

### 📁 Core Modules

#### `config.py` - Configuration & Constants
**Purpose**: Centralized configuration, styling, and constants

```python
# Contains:
- App metadata (title, port)
- Graph settings (spacing, layout parameters)
- LLM configuration (retry settings, term counts)
- Color scheme and styling
- Button and layout styles
- Animation settings
- HTML template
```

#### `components.py` - UI Component Factory
**Purpose**: Reusable UI component creation functions

```python
# Key functions:
- create_app_header()           # Main title
- create_data_stores()          # Dash stores for state
- create_timers()               # Animation timers
- create_toggle_button()        # Explanation length toggle
- create_reload_button()        # Reload explanation
- create_graph_component()      # Graph visualization
- create_info_box_content()     # Info panel content
- create_suggested_concepts()   # Suggestion buttons
- create_main_layout()          # Complete layout
```

#### `state_manager.py` - Application State Logic
**Purpose**: Manages app state, LLM interactions, and state transitions

```python
# Core methods:
- get_initial_state()           # Default app state
- create_new_concept_map()      # New concept exploration
- expand_concept_map()          # Add child concepts
- generate_explanation()        # LLM explanation generation
- get_suggested_concepts()      # Concept suggestions
- update_explanation_length()   # Toggle short/long
- load_state_from_upload()      # File import
- export_state_for_download()   # File export
```

#### `graph_manager.py` - Graph Visualization Logic
**Purpose**: Handles graph layout, positioning, and visualization

```python
# Core methods:
- build_node_positions()        # Tree-based positioning
- apply_force_directed_layout() # Physics-based optimization
- calculate_visual_properties() # Node/edge styling
- generate_figure()             # Complete Plotly figure
- autoscale_figure()           # Auto-fit viewport
```

#### `callback_handlers.py` - Organized Callbacks
**Purpose**: Organizes all Dash callbacks into logical groups

```python
# Callback groups:
- register_initialization_callbacks()  # App startup/reset
- register_interaction_callbacks()     # User interactions
- register_control_callbacks()         # Toggle/reload buttons
- register_animation_callbacks()       # Visual effects
- register_ui_callbacks()             # UI updates
```

### 📁 Main Application

#### `app.py` - Application Entry Point
**Purpose**: Minimal main file that assembles the modular components

```python
# Simplified to:
- Import all modules
- Create app layout using components
- Initialize callback handlers
- Run the application
```

## Data Flow

```
User Input → CallbackHandlers → StateManager → GraphManager → Components → UI Update
                     ↓
               LLM Integration (Gemini API)
```

## How to Extend

### Adding New UI Components
1. Add component factory function to `components.py`
2. Add styling to `config.py` if needed
3. Use in layout creation

### Adding New Functionality
1. Add business logic to `state_manager.py`
2. Add visualization logic to `graph_manager.py` if needed
3. Add callbacks to `callback_handlers.py`
4. Update components as necessary

### Modifying Styling
1. Update color scheme or styles in `config.py`
2. Changes automatically propagate to all components

### Adding New Configuration
1. Add constants to appropriate section in `config.py`
2. Use throughout other modules

## File Organization

```
elie/
├── app.py                  # Main application (99 lines)
├── config.py              # Configuration & constants
├── components.py           # UI component factories
├── state_manager.py        # Application state logic
├── graph_manager.py        # Graph visualization
├── callback_handlers.py    # Organized callbacks
├── gemini_calls.py         # LLM API integration
├── prompting.py           # LLM prompt management
└── modal_llm.py           # Alternative LLM provider
```

## Benefits for Maintenance

### Before Modularization
- ❌ 965 lines in single file
- ❌ Mixed concerns (UI, logic, styling)
- ❌ Hard to find specific functionality
- ❌ Difficult to modify without breaking other parts
- ❌ Complex callback interdependencies

### After Modularization
- ✅ Clear separation of concerns
- ✅ Easy to locate and modify specific features
- ✅ Reusable components
- ✅ Centralized configuration
- ✅ Logical code organization
- ✅ Human-readable structure
- ✅ Simple to extend and maintain

## Testing

The modular structure makes testing easier:
- Each module can be tested independently
- State management is isolated and predictable
- UI components can be tested in isolation
- Graph logic is separate from app logic

## Performance

The modular structure maintains all original performance characteristics while improving:
- **Code maintainability** - easier to optimize specific parts
- **Development speed** - faster to locate and modify code
- **Debugging** - clearer error traces and isolated concerns 