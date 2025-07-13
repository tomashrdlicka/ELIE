"""
Callback Handlers module for ELIE app
Organizes all Dash callbacks into logical groups and functions
"""

from dash import Input, Output, State, ALL, ctx, no_update
from components import (
    create_graph_component, create_info_box_content, 
    create_suggested_concepts_section
)
from state_manager import StateManager
from graph_manager import GraphManager


class CallbackHandlers:
    """Organizes and manages all app callbacks with decoupled architecture"""
    
    def __init__(self, app):
        self.app = app
        self.register_all_callbacks()
    
    def register_all_callbacks(self):
        """Register all callbacks with the app"""
        self.register_initialization_callbacks()
        self.register_state_interaction_callbacks()
        self.register_control_callbacks()
        self.register_animation_callbacks()
        self.register_ui_callbacks()
    
    def register_initialization_callbacks(self):
        """Register callbacks for app initialization and reset"""
        
        @self.app.callback(
            [Output("graph-container", "children"), 
             Output("upload-graph", "contents"),
             Output("input-overlay-visible", "data"), 
             Output("start-input", "value"), 
             Output("app-state-store", "data"),
             Output("graph-key", "data"), 
             Output("input-flash", "data"), 
             Output("node-flash", "data"),
             Output('toggle-animating', 'data'),
             Output('submit-btn-flash', 'data', allow_duplicate=True),
             Output('reload-triggered', 'data', allow_duplicate=True),
             Output('reload-spinning', 'data'),
             Output('reload-last-click', 'data'),
             Output('reload-timer', 'n_intervals'),
             Output('explanation-length-flag', 'data')],
            [Input("reset-term-btn", "n_clicks")],
            [State("graph-key", "data")],
            prevent_initial_call=True
        )
        def initialize_app(reset_clicks, graph_key):
            """Handle reset button clicks - completely separate from info-box updates"""
            print("Initializing app state...")
            
            # Create initial state
            initial_state = StateManager.get_initial_state()
            
            # Create initial graph
            fig = GraphManager.generate_figure(
                initial_state['node_data'], 
                initial_state['clicked_nodes_list'], 
                initial_state['last_clicked'], 
                node_flash=None
            )
            fig = GraphManager.autoscale_figure(fig)
            new_key = graph_key + 1 if graph_key else 1
            
            graph_component = create_graph_component(fig, new_key)
            
            return (
                [graph_component], 
                None,  # clear upload contents
                True,  # show input overlay
                "",    # clear input value
                initial_state, 
                new_key, 
                False, # no input flash
                None,  # no node flash
                False,    # no toggle animation
                False,     # no submit button flash
                False,     # no reload triggered
                False,     # no reload spinning
                0,         # reset reload last click count
                0,         # reset reload timer intervals
                'short'    # reset explanation length flag to short
            )
    
    def register_state_interaction_callbacks(self):
        """Register callbacks that only update state and graph - NO UI UPDATES"""
        
        @self.app.callback(
            [Output("graph-container", "children", allow_duplicate=True), 
             Output("upload-graph", "contents", allow_duplicate=True),
             Output("input-overlay-visible", "data", allow_duplicate=True), 
             Output("start-input", "value", allow_duplicate=True), 
             Output("app-state-store", "data", allow_duplicate=True),
             Output("graph-key", "data", allow_duplicate=True), 
             Output("input-flash", "data", allow_duplicate=True), 
             Output("node-flash", "data", allow_duplicate=True)],
            [Input({'type': 'graph', 'key': ALL}, 'clickData'), 
             Input("start-input", "n_submit"), 
             Input("upload-graph", "contents"),
             Input("submit-btn", "n_clicks")],
            [State("start-input", "value"), 
             State("app-state-store", "data"), 
             State("graph-key", "data"), 
             State("explanation-length-flag", "data")],
            prevent_initial_call=True
        )
        def handle_interaction(clickData_list, input_submit, upload_contents, submit_clicks, 
                             user_input, state, graph_key, explanation_length_flag):
            """Handle all main interactions - GRAPH AND STATE ONLY"""
            trigger_id = ctx.triggered[0]["prop_id"].split(".")[0] if ctx.triggered else None
            clickData = next((cd for cd in clickData_list if cd), None)

            if trigger_id == "upload-graph" and upload_contents is not None:
                return self._handle_file_upload(upload_contents, explanation_length_flag, 
                                               graph_key)
            
            if (trigger_id == "start-input" or trigger_id == "submit-btn") and user_input:
                return self._handle_concept_submission(user_input.strip(), explanation_length_flag, 
                                                     graph_key)
            
            if clickData and "points" in clickData:
                return self._handle_node_click(clickData, state, explanation_length_flag, 
                                             graph_key)
            
            return [no_update] * 8
        
        @self.app.callback(
            [Output("graph-container", "children", allow_duplicate=True), 
             Output("upload-graph", "contents", allow_duplicate=True),
             Output("input-overlay-visible", "data", allow_duplicate=True), 
             Output("start-input", "value", allow_duplicate=True), 
             Output("app-state-store", "data", allow_duplicate=True),
             Output("graph-key", "data", allow_duplicate=True), 
             Output("input-flash", "data", allow_duplicate=True), 
             Output("node-flash", "data", allow_duplicate=True)],
            [Input({'type': 'suggested-term', 'term': ALL}, 'n_clicks')],
            [State({'type': 'suggested-term', 'term': ALL}, 'id'), 
             State("app-state-store", "data"), 
             State("graph-key", "data"), 
             State("explanation-length-flag", "data")],
            prevent_initial_call=True
        )
        def handle_suggested_term_click(all_n_clicks, all_btn_ids, state, graph_key, 
                                      explanation_length_flag):
            """Handle suggested term button clicks - GRAPH AND STATE ONLY"""
            if not ctx.triggered or not all_n_clicks or not all_btn_ids:
                return [no_update] * 8
            
            # Find which button was clicked
            clicked_idx = None
            for i, n in enumerate(all_n_clicks):
                if n and n > 0:
                    clicked_idx = i
                    break
            
            if clicked_idx is None:
                return [no_update] * 8
            
            term = all_btn_ids[clicked_idx]['term']
            print(f"[SUGGESTED TERM CLICKED] {term}")
            
            return self._handle_concept_submission(term, explanation_length_flag, 
                                                 graph_key, flash_input=True)
    
    def register_control_callbacks(self):
        """Register callbacks for control buttons (toggle, reload)"""
        
        @self.app.callback(
            [Output('explanation-length-flag', 'data', allow_duplicate=True),
             Output('app-state-store', 'data', allow_duplicate=True)],
            Input('toggle-explanation-btn', 'n_clicks'),
            [State('explanation-length-flag', 'data'),
             State('app-state-store', 'data')],
            prevent_initial_call=True
        )
        def toggle_explanation_length(n_clicks, current_flag, state):
            """Toggle explanation length and regenerate"""
            if n_clicks is None:
                return current_flag, no_update
            
            new_flag = 'long' if current_flag == 'short' else 'short'
            
            if not StateManager.has_valid_concept(state):
                return new_flag, no_update
            
            new_state = StateManager.update_explanation_length(state, new_flag)
            return new_flag, new_state
        
        @self.app.callback(
            [Output('reload-triggered', 'data', allow_duplicate=True),
             Output('reload-spinning', 'data', allow_duplicate=True),
             Output('reload-timer', 'disabled', allow_duplicate=True),
             Output('reload-last-click', 'data', allow_duplicate=True),
             Output('reload-timer', 'n_intervals', allow_duplicate=True)],
            Input('reload-explanation-btn', 'n_clicks'),
            State('reload-last-click', 'data'),
            prevent_initial_call=True
        )
        def trigger_reload_process(n_clicks, last_click_count):
            """Start reload process when button is clicked"""
            print(f"[trigger_reload_process] n_clicks: {n_clicks}, last_click_count: {last_click_count}")
            
            # Only trigger if this is a new click (n_clicks increased)
            if n_clicks and n_clicks > (last_click_count or 0):
                print("[trigger_reload_process] New click detected - starting reload process")
                return True, True, False, 0, 0  # Reset last_click_count to 0 immediately when starting new reload
            
            print("[trigger_reload_process] No new click detected")
            return False, False, True, last_click_count or 0, no_update  # No change, keep last click count
        
        @self.app.callback(
            [Output('app-state-store', 'data', allow_duplicate=True),
             Output('reload-spinning', 'data', allow_duplicate=True),
             Output('reload-triggered', 'data', allow_duplicate=True),
             Output('reload-timer', 'disabled', allow_duplicate=True),
             Output('reload-explanation-btn', 'n_clicks')],  # Only reset n_clicks here
            Input('reload-timer', 'n_intervals'),
            [State('app-state-store', 'data'), 
             State('explanation-length-flag', 'data'),
             State('reload-triggered', 'data')],
            prevent_initial_call=True
        )
        def reload_explanation(n_intervals, state, length_flag, reload_triggered):
            """Generate new explanation when timer fires"""
            print(f"[reload_explanation] n_intervals: {n_intervals}, reload_triggered: {reload_triggered}")
            
            # Only proceed if reload was triggered and timer has fired
            if not reload_triggered or n_intervals < 1:
                return no_update, no_update, no_update, no_update, no_update
            
            if not StateManager.has_valid_concept(state):
                print("[reload_explanation] No valid concept, stopping spinner")
                return no_update, False, False, True, 0  # Only reset n_clicks
            
            print(f"[reload_explanation] Generating new explanation with length_flag: {length_flag}")
            new_state = StateManager.reload_explanation(state, length_flag)
            print("[reload_explanation] Explanation generated, stopping spinner")
            return new_state, False, False, True, 0  # Only reset n_clicks after successful reload
        
        @self.app.callback(
            Output("download-graph", "data"),
            Input("save-btn", "n_clicks"),
            State("app-state-store", "data"),
            prevent_initial_call=True
        )
        def save_graph(n_clicks, state):
            """Handle graph export/download"""
            if n_clicks:
                content = StateManager.export_state_for_download(state)
                return dict(content=content, filename="elie_graph.json")
            return no_update
    
    def register_animation_callbacks(self):
        """Register callbacks for animations and visual effects"""
        
        @self.app.callback(
            Output('submit-btn-flash', 'data', allow_duplicate=True),
            [Input('start-input', 'n_submit'), Input('submit-btn', 'n_clicks')],
            prevent_initial_call=True
        )
        def trigger_submit_btn_flash(n_submit, n_clicks):
            """Trigger submit button flash animation"""
            return True if ctx.triggered else no_update
        

    
    def register_ui_callbacks(self):
        """Register callbacks for UI updates ONLY - these have exclusive ownership of UI elements"""
        
        @self.app.callback(
            Output('info-box', 'children'),
            [Input('app-state-store', 'data'),
             Input('explanation-length-flag', 'data'),
             Input('reload-spinning', 'data')],
            prevent_initial_call='initial_duplicate'  # Allow initial call but handle duplicates
        )
        def update_info_box_on_state_change(state, length_flag, reload_spinning):
            """Update info box when state, flag, or reload state changes - EXCLUSIVE OWNERSHIP"""
            if not StateManager.has_valid_concept(state):
                return create_info_box_content(explanation=state.get('explanation_paragraph', ''))
            
            term = StateManager.get_current_term(state)
            explanation = state.get('explanation_paragraph', '')
            
            return create_info_box_content(
                term=term, explanation=explanation, length_flag=length_flag, spinning=reload_spinning
            )
        
        @self.app.callback(
            Output("suggested-concepts-container", "children"),
            Input("app-state-store", "data"),
        )
        def update_suggested_concepts(state):
            """Update suggested concepts based on current state"""
            suggestions = StateManager.get_suggested_concepts(state)
            return create_suggested_concepts_section(suggestions)
        
        @self.app.callback(
            [Output("centered-input-overlay", "style"),
             Output("submit-btn-flash", "data", allow_duplicate=True)],
            Input("input-overlay-visible", "data"),
            prevent_initial_call=True
        )
        def toggle_overlay(visible):
            """Toggle input overlay visibility and reset submit button flash"""
            base_style = {
                "position": "absolute",
                "left": "50%",
                "top": "50%",
                "transform": "translate(-50%, -50%)",
                "zIndex": 10,
                "width": "100%",
                "display": "flex",
                "justifyContent": "center",
                "alignItems": "center",
                "transition": "opacity 0.3s ease, transform 0.3s ease"
            }
            if visible:
                return {**base_style, 
                       "opacity": 1, 
                       "pointerEvents": "auto"}, False
            else:
                return {**base_style, 
                       "transform": "translate(-50%, -40%)",  # Move up when hidden
                       "opacity": 0, 
                       "pointerEvents": "none"}, False
    
    # Helper methods for complex interactions
    def _handle_file_upload(self, upload_contents, explanation_length_flag, graph_key):
        """Handle file upload and state loading"""
        new_state = StateManager.load_state_from_upload(upload_contents)
        if not new_state:
            return [no_update] * 8
        
        fig = GraphManager.generate_figure(
            new_state['node_data'], new_state['clicked_nodes_list'], 
            new_state['last_clicked'], node_flash=None
        )
        fig = GraphManager.autoscale_figure(fig)
        new_key = graph_key + 1
        graph_component = create_graph_component(fig, new_key)
        
        return ([graph_component], None, False, no_update, 
                new_state, new_key, False, None)
    
    def _handle_concept_submission(self, term, explanation_length_flag, 
                                 graph_key, flash_input=False):
        """Handle new concept submission"""
        # Always use 'short' for new concepts to ensure consistent behavior
        new_state = StateManager.create_new_concept_map(term, 'short')
        if not new_state:
            return [no_update] * 8
        
        fig = GraphManager.generate_figure(
            new_state['node_data'], new_state['clicked_nodes_list'], 
            new_state['last_clicked'], node_flash=None
        )
        fig = GraphManager.autoscale_figure(fig)
        new_key = graph_key + 1
        graph_component = create_graph_component(fig, new_key)
        
        return ([graph_component], no_update, False, no_update, 
                new_state, new_key, flash_input, None)
    
    def _handle_node_click(self, clickData, state, explanation_length_flag, graph_key):
        """Handle node click interactions"""
        clicked = clickData["points"][0].get("customdata")
        if not clicked or (clicked == "start" and clicked in state['clicked_nodes_list']):
            return [no_update] * 8
        
        if clicked not in state['clicked_nodes_list']:
            new_state = StateManager.expand_concept_map(state, clicked)
            
            fig = GraphManager.generate_figure(
                new_state['node_data'], new_state['clicked_nodes_list'], 
                new_state['last_clicked'], node_flash=clicked
            )
            fig = GraphManager.autoscale_figure(fig)
            new_key = graph_key + 1
            graph_component = create_graph_component(fig, new_key)
            
            return ([graph_component], no_update, False, no_update, 
                    new_state, new_key, False, None)
        else:
            return [no_update] * 8 