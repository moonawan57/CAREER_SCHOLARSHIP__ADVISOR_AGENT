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

# Test 1: Scholarship abroad
print("=== Test 1: I want a scholarship abroad ===")
messages = [
    {"role": "assistant", "content": "Hi! I'm your Career & Scholarship Advisor. Tell me about your background, interests, and goals to get started."},
    {"role": "user", "content": "I want to pursue a scholarship abroad"}
]
result = chat(messages, 0)
print(result['reply'])
print()

# Test 2: Make a CV
print("=== Test 2: Can you make me a CV? ===")
messages = [
    {"role": "assistant", "content": "Hi! I'm your Career & Scholarship Advisor. Tell me about your background, interests, and goals to get started."},
    {"role": "user", "content": "Can you make me a CV?"}
]
result = chat(messages, 0)
print(result['reply'])
print()

# Test 3: Simple info
print("=== Test 3: What careers are good for CS students? ===")
messages = [
    {"role": "assistant", "content": "Hi! I'm your Career & Scholarship Advisor. Tell me about your background, interests, and goals to get started."},
    {"role": "user", "content": "What careers are good for CS students?"}
]
result = chat(messages, 0)
print(result['reply'])
