
    
def build_starter_prompt(concept):
    return (f"Given that I want to understand {concept}, give me a comma-separated list of concepts "
            f"which are necessary to understand {concept}. Do not include anything else in your answer. "
            f"Give me only 4  concepts and their semantic distance from {concept} (the distance should be in range 0-1, where zero is closest, 1 is furthest and the concepts can have the same but also different distance)")
    

def build_further_prompt(concept, excluded_concepts):
    return (f"Given that I want to understand {concept}, give me a comma-separated list of concepts "
            f"which are necessary to understand {concept}. Do not include anything else in your answer. "
            f"Give me only 3  concepts and their semantic distance from {concept} (the distance should be in range 0-1, where zero is closest, 1 is furthest and the concepts can have the same but also different distance), Please exclude {excluded_concepts}")
    

def build_final_prompt(concept, included_concepts, excluded_concepts):
    return (f"Given that I understand {included_concepts} and I do not understand {excluded_concepts}, please explain {concept} to me. "
            f"Make the explanation concise and clear and make sure to take into account what topics I know and which I do not know. "
            f"Given the context that I provided go directly to the explanation and do not repeat to me what I already know. "
            f"If suitable, use analogies related to the concepts I do know to fill in the gaps caused by the terms I do not know.")
    
    
def parse_terms(response):
    parts = [item.strip() for item in response.split(",")]
    return {
        parts[i]: {
            "distance": float(parts[i + 1]),
            "breadth": float(parts[i + 2])
        }
        for i in range(0, len(parts), 3)
    }