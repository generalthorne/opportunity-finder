import ollama

response = ollama.chat(
    model="qwen3:8b",
    messages=[
        {
            "role": "user",
            "content": "Return a JSON object with one key, status, set to success."
        }
    ],
    format="json",
    think=False,
    options={"temperature": 0},
)

print("Response:", repr(response.message.content))
print("Done:", response.done)
print("Done reason:", response.done_reason)
print("Full response:")
print(response.model_dump_json(indent=2))