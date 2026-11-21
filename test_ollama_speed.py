import time
import ollama

print("Sending request...", flush=True)

start = time.time()

response = ollama.chat(
    model="qwen3:4b",
    messages=[
        {
            "role": "user",
            "content": (
                'Identify the opportunity in this text: '
                '"The PEY Co-op is a paid, optional program at '
                'the University of Toronto. Return JSON with '
                'title, organization, and category.'
            )
        }
    ],
    format="json",
    think=False
)

elapsed = time.time() - start

print("Response received.", flush=True)
print("Time:", round(elapsed, 2), "seconds")
print("Response:", response.message.content)