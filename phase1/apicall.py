from openai import OpenAI

client = OpenAI(
    api_key="AIzaSyA-qjPKmPGiFNhBqLVSQY4rPvp3LNa3oL4",
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
)

response = client.chat.completions.create(
    model="gemini-2.5-flash",
    messages=[{"role": "user", "content": "What is an embedding vector?"}]
)

print(response.choices[0].message.content)
print(response.usage.prompt_tokens)
print(response.usage.completion_tokens)