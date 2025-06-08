import os
import json
import requests
from elie.prompting import *

# READ modal LLM API endpoint and key from environment variables
LLM_ENDPOINT = os.getenv("LLM_ENDPOINT")
LLM_HEADERS = {
    "Authorization": f"Bearer {os.getenv('LLM_API_KEY')}",
    "Content-Type": "application/json",
}
MODEL_NAME = "neuralmagic/Meta-Llama-3.1-8B-Instruct-quantized.w4a16"


def call_modal_llm(prompt):
    messages = [{"role": "user", "content": prompt}]
    print(f"Sending a sample message to {LLM_ENDPOINT}", *messages, sep="\n")

    headers = LLM_HEADERS.copy()
    payload = json.dumps({"messages": messages, "model": MODEL_NAME})
    try:
        response = requests.post(
            LLM_ENDPOINT + "/v1/chat/completions",
            data=payload.encode("utf-8"),
            headers=headers,
        )
        response.raise_for_status()
        data = json.loads(response.text)
        # Get the content fo the first choice
        data = data["choices"][0]["message"]["content"]

    except requests.RequestException as e:
        return f"❌ Error reaching LLM: {e}"

    return data


if __name__ == "__main__":
    response = call_modal_llm(build_further_prompt("quaternion", ["3D", "4D"], ["vectors", "rotation matrices"]))
    print(f"Modal LLM response: {response}")
    print(parse_terms(response))