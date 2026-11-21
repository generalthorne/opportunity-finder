import ollama

print("Sending JSON request...", flush=True)

response = ollama.chat(
    model="qwen3:4b",
    messages=[
        {
            "role": "user",
            "content": 'Return exactly this JSON: {"status":"working"}'
        }
    ],
    format="json",
    think=False
)

print("Response received.", flush=True)
print("CONTENT:", repr(response.message.content))