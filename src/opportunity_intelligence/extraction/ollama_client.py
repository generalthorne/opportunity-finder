"""Client for communicating with a local Ollama model."""

import ollama


DEFAULT_MODEL = "gemma4:12b"


def generate_response(
    prompt: str,
    model: str = DEFAULT_MODEL,
    response_format: dict | str | None = None
) -> str:
    """Generate a response using the configured Ollama model."""

    request_options = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": prompt
            }
        ],
        "think": False
    }

    if response_format is not None:
        request_options["format"] = response_format

    response = ollama.chat(**request_options)

    return response.message.content.strip()