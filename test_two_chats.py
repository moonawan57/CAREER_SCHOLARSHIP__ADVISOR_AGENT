import urllib.request
import json
import sys

sys.stdout.reconfigure(encoding='utf-8')

backend_url = "https://ferrari-paul-beijing-opposite.trycloudflare.com"

def chat(messages, turn):
    req = urllib.request.Request(
        f"{backend_url}/chat",
        data=json.dumps({"messages": messages, "turn": turn}).encode(),
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    response = urllib.request.urlopen(req)
    return json.loads(response.read().decode())

messages = [
    {"role": "assistant", "content": "Hi! I'm your Career & Scholarship Advisor. Tell me about your background, interests, and goals to get started."},
]

# First chat
print("=== Chat 1 ===")
messages.append({"role": "user", "content": "I want a scholarship abroad"})
result1 = chat(messages, 0)
print(f"is_final: {result1['is_final']}")
print(f"reply: {result1['reply'][:200]}")
messages.append({"role": "assistant", "content": result1['reply']})
print()

# Second chat
print("=== Chat 2 ===")
messages.append({"role": "user", "content": "I am a CS student with 3.8 GPA"})
result2 = chat(messages, 1)
print(f"is_final: {result2['is_final']}")
print(f"reply: {result2['reply'][:200]}")
