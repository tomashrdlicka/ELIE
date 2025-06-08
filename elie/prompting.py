
import re
  
def build_starter_prompt(concept):
    return (f"Given that I want to understand {concept}, give me a comma-separated list of concepts "
            f"which are necessary to understand {concept}. Do not include anything else in your answer. "
            f"Give me only 4  concepts, their semantic distance from {concept} (the distance should be in range 0.1-1 with a step of 0.1) and  the breadth of the concept (the breadth should be in range 0.1-1 with a step of 0.1)."
            f"The answer should be in the following format: concept1,distance1,breadth1,concept2,distance2,breadth2,concept3,distance3,breadth3,concept4,distance4,breadth4"
            f"Please only answer in english."
            f"this is an exaple of how the output should look:Modal LLM response:" 
            f"Linear Algebra,0.1,1 \n"
            f"Vectors,0.3,0.8 \n"
            f"4-D Coordinate System,0.5,0.9 \n"
            f"Rotation Matrices,0.8,0.7")
    

def build_further_prompt(concept, excluded_concepts, included_concepts):
    return (
        f"Given that I want to understand {concept}, give me a comma-separated list of concepts "
        f"which are necessary to understand {concept}. Do not include anything else in your answer. "
        f"Make sure to give me only 3 concepts, their semantic distance from {concept} (the distance should be in range 0.1–1 with a step of 0.1) "
        f"and the breadth of the concept (the breadth should be in range 0.1–1 with a step of 0.1). "
        f"Please exclude the following concepts: {', '.join(excluded_concepts)} and {', '.join(included_concepts)}. "
        f"The answer should be in the following format: concept1,distance1,breadth1,concept2,distance2,breadth2,concept3,distance3,breadth3. "
        f"Please only answer in English. "
        f"This is an example of how the output should look: Modal LLM response: Linear Algebra,0.6,1,Vectors,0.7,0.8,Rotation Matrices,0.9,0.7"
    )


def build_final_prompt(concept, included_concepts, excluded_concepts):
    return (
        f"Given that I understand {', '.join(included_concepts)} and I do not understand {', '.join(excluded_concepts)}, "
        f"please explain {concept} to me. Make the explanation concise and clear and make sure to take into account what "
        f"topics I know and which I do not know. Given the context that I provided go directly to the explanation and do not "
        f"repeat to me what I already know. If suitable, use analogies related to the concepts I do know to fill in the gaps "
        f"caused by the terms I do not know."
    )

def parse_terms(response, num_terms=4):
    # First, try to match the verbose format with labels
    verbose_pattern = r'([\w\s\-&]+?)\s*,?\s*distance\s*=\s*([0-9.]+)\s*,\s*breadth\s*=\s*([0-9.]+)'
    verbose_matches = re.findall(verbose_pattern, response)

    result = {}

    if verbose_matches:
        for i, (term, distance, breadth) in enumerate(verbose_matches):
            if i >= num_terms:
                break
            result[term.strip()] = {
                "distance": float(distance),
                "breadth": float(breadth)
            }
        return result

    # Fallback: try to parse the compact format (term, distance, breadth every 3 items)
    parts = [item.strip() for item in response.replace("\n", ",").split(",") if item.strip()]
    
    try:
        for i in range(0, min(len(parts), num_terms * 3), 3):
            term = parts[i]
            distance = float(parts[i + 1])
            breadth = float(parts[i + 2])
            result[term] = {"distance": distance, "breadth": breadth}
    except (IndexError, ValueError):
        print("⚠️ Warning: Malformed response, could not parse all items cleanly.")

    return result

