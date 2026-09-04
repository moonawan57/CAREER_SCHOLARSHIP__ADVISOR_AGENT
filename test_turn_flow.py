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

print("=== Testing conversation flow ===")
for turn in range(20):
    user_msg = f"Answer for turn {turn + 1}"
    messages.append({"role": "user", "content": user_msg})
    result = chat(messages, turn)
    print(f"Turn {turn:2d}: is_final={result['is_final']} | reply={result['reply'][:60]}...")
    messages.append({"role": "assistant", "content": result['reply']})
    if result['is_final']:
        print(f"\nFinal recommendation reached at turn {turn}")
        break
else:
    print("\nReached maximum loop without final")
