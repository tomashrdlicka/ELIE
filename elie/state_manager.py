"""
State Management module for ELIE app
Handles application state logic, LLM interactions, and state transitions
"""

import time
import json
import base64
from gemini_calls import call_gemini_llm
from prompting import (
    build_starter_prompt, parse_terms, build_further_prompt,
    build_short_final_prompt, build_long_final_prompt, get_more_concepts
)
from config import HOW_IT_WORKS_MD, LLM_CONFIG


class StateManager:
    """Manages application state and LLM interactions"""
    
    @staticmethod
    def get_initial_state():
        """Returns the default state for the application"""
        return {
            "node_data": {"start": {"parent": None, "distance": 0.0, "label": ""}},
            "clicked_nodes_list": [],
            "unclicked_nodes": [],
            "explanation_paragraph": HOW_IT_WORKS_MD,
            "last_clicked": "start"
        }
    
    @staticmethod
    def recompute_node_distances(node_data):
        """Ensure all nodes have baseline distance and breadth values"""
        for node, data in node_data.items():
            # Breadth (node size) calculation
            if 'raw_breadth' not in data:
                # The start node is smaller than other nodes
                data['raw_breadth'] = 0.8 if data['parent'] is None else 1.2
            data['breadth'] = data['raw_breadth']

            # Distance (edge length) calculation (only for non-root nodes)
            if data["parent"] is not None:
                if 'raw_distance' not in data:
                    data['raw_distance'] = 1.0
                data['distance'] = data['raw_distance']
    
    @staticmethod
    def call_llm_with_retry(prompt_func, *args, max_retries=5):
        """Call LLM with retry logic for robustness"""
        for attempt in range(max_retries):
            try:
                prompt = prompt_func(*args)
                llm_response = call_gemini_llm(prompt)
                
                if prompt_func in [build_starter_prompt, build_further_prompt]:
                    # Parse response for concept extraction
                    num_terms = LLM_CONFIG["starter_terms"] if prompt_func == build_starter_prompt else LLM_CONFIG["further_terms"]
                    parsed = parse_terms(llm_response, num_terms=num_terms)
                    if parsed:  # Check if parsing was successful
                        return parsed
                else:
                    # Return raw response for explanation prompts
                    return llm_response
                    
            except Exception as e:
                print(f"LLM call/parsing failed (attempt {attempt + 1}). Error: {e}")
                if attempt < max_retries - 1:
                    time.sleep(LLM_CONFIG["retry_delay"])
                else:
                    print(f"Failed after {max_retries} attempts")
                    return None
        
        return None
    
    @staticmethod
    def create_new_concept_map(term, explanation_length_flag="short"):
        """Create a new concept map for the given term"""
        parsed_terms = StateManager.call_llm_with_retry(build_starter_prompt, term)
        
        if not parsed_terms:
            print("Failed to parse terms from LLM. Cannot create concept map.")
            return None

        node_data = {"start": {"parent": None, "distance": 0.0, "label": term}}
        for child_term, props in parsed_terms.items():
            node_data[child_term] = {
                "parent": "start",
                "distance": props["distance"],
                "raw_distance": props["distance"],
                "breadth": props["breadth"],
                "raw_breadth": props["breadth"]
            }
        
        StateManager.recompute_node_distances(node_data)
        
        new_state = {
            "node_data": node_data,
            "clicked_nodes_list": [],
            "unclicked_nodes": [k for k in node_data.keys() if k != "start"],
            "last_clicked": "start"
        }
        
        # Generate initial explanation
        explanation = StateManager.generate_explanation(
            term, new_state['clicked_nodes_list'], 
            new_state['unclicked_nodes'], explanation_length_flag
        )
        new_state["explanation_paragraph"] = explanation
        
        return new_state
    
    @staticmethod
    def expand_concept_map(state, clicked_node):
        """Expand the concept map by adding children to a clicked node"""
        if clicked_node in state['clicked_nodes_list']:
            return state  # Already expanded
        
        new_state = state.copy()
        new_state['clicked_nodes_list'].append(clicked_node)
        if clicked_node in new_state['unclicked_nodes']:
            new_state['unclicked_nodes'].remove(clicked_node)

        initial_term = new_state['node_data']["start"].get("label", "start")
        
        parsed_terms = StateManager.call_llm_with_retry(
            build_further_prompt, 
            initial_term, 
            new_state['unclicked_nodes'], 
            new_state['clicked_nodes_list']
        )

        if not parsed_terms:
            print("Failed to parse further terms from LLM. Cannot expand concept map.")
            return new_state

        for child_term, props in parsed_terms.items():
            if child_term not in new_state['node_data']:
                new_state['node_data'][child_term] = {
                    "parent": clicked_node,
                    "distance": props["distance"],
                    "raw_distance": props["distance"],
                    "breadth": props["breadth"],
                    "raw_breadth": props["breadth"]
                }
                if child_term not in new_state['unclicked_nodes'] and child_term not in new_state['clicked_nodes_list']:
                    new_state['unclicked_nodes'].append(child_term)

        StateManager.recompute_node_distances(new_state['node_data'])
        new_state['last_clicked'] = clicked_node
        
        return new_state
    
    @staticmethod
    def generate_explanation(term, included_concepts, excluded_concepts, length_flag="short"):
        """Generate explanation for the given term and context"""
        if length_flag == "short":
            prompt_func = build_short_final_prompt
        else:
            prompt_func = build_long_final_prompt
        
        explanation = StateManager.call_llm_with_retry(
            prompt_func, term, included_concepts, excluded_concepts
        )
        
        return explanation or "Failed to generate explanation. Please try again."
    
    @staticmethod
    def get_suggested_concepts(state):
        """Get suggested concepts based on current state"""
        node_data = state.get("node_data", {})
        if not node_data or not node_data.get("start", {}).get("label"):
            return []
        
        known = state.get("unclicked_nodes", [])
        unknown = state.get("clicked_nodes_list", [])
        
        try:
            prompt = get_more_concepts(known, unknown)
            llm_response = call_gemini_llm(prompt)
            # Parse comma-separated concepts (no distances/breadths)
            suggestions = [s.strip() for s in llm_response.split(",") if s.strip()][:LLM_CONFIG["suggestion_terms"]]
            return suggestions
        except Exception as e:
            print(f"Failed to get suggested concepts: {e}")
            return []
    
    @staticmethod
    def load_state_from_upload(upload_contents):
        """Load state from uploaded JSON file"""
        try:
            _, content_string = upload_contents.split(',')
            data = json.loads(base64.b64decode(content_string).decode('utf-8'))
            
            new_state = {
                "node_data": data.get("node_data", {}),
                "clicked_nodes_list": data.get("clicked_nodes_list", []),
                "unclicked_nodes": data.get("unclicked_nodes", []),
                "explanation_paragraph": data.get("explanation", HOW_IT_WORKS_MD),
                "last_clicked": "start"
            }
            
            StateManager.recompute_node_distances(new_state['node_data'])
            return new_state
            
        except Exception as e:
            print(f"Failed to load state from upload: {e}")
            return None
    
    @staticmethod
    def export_state_for_download(state):
        """Export state for download as JSON"""
        export_data = {
            "node_data": state['node_data'],
            "clicked_nodes_list": state['clicked_nodes_list'],
            "unclicked_nodes": state['unclicked_nodes'],
            "explanation": state['explanation_paragraph']
        }
        return json.dumps(export_data, indent=2)
    
    @staticmethod
    def update_explanation_length(state, new_length_flag):
        """Update explanation with new length setting"""
        node_data = state.get('node_data', {})
        if not node_data or not node_data.get('start', {}).get('label'):
            return state
        
        term = node_data['start'].get('label', 'start')
        included = state.get('clicked_nodes_list', [])
        excluded = state.get('unclicked_nodes', [])
        
        new_explanation = StateManager.generate_explanation(
            term, included, excluded, new_length_flag
        )
        
        new_state = state.copy()
        new_state['explanation_paragraph'] = new_explanation
        
        return new_state
    
    @staticmethod
    def reload_explanation(state, length_flag):
        """Reload explanation with current settings"""
        return StateManager.update_explanation_length(state, length_flag)
    
    @staticmethod
    def get_current_term(state):
        """Get the current root term from state"""
        node_data = state.get('node_data', {})
        return node_data.get('start', {}).get('label', '')
    
    @staticmethod
    def has_valid_concept(state):
        """Check if state has a valid concept loaded"""
        return bool(StateManager.get_current_term(state)) 