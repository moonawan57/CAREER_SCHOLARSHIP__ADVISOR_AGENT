import urllib.request
import json
import sys

sys.stdout.reconfigure(encoding='utf-8')

backend_url = "https://ferrari-paul-beijing-opposite.trycloudflare.com"

messages = [
    {"role": "assistant", "content": "Hi! I'm your Career & Scholarship Advisor. Tell me about your background, interests, and goals to get started."},
    {"role": "user", "content": "computer science career"}
]

req = urllib.request.Request(
    f"{backend_url}/chat",
    data=json.dumps({"messages": messages, "turn": 0}).encode(),
    headers={"Content-Type": "application/json"},
    method="POST"
)

response = urllib.request.urlopen(req)
data = json.loads(response.read().decode())
print("Status:", response.status)
print("is_final:", data['is_final'])
print("Reply:")
print(data['reply'])
print("\nWord count:", len(data['reply'].split()))
