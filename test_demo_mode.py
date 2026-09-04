import urllib.request
import json
import sys

sys.stdout.reconfigure(encoding='utf-8')

backend_url = "https://ferrari-paul-beijing-opposite.trycloudflare.com"

def chat(user_message):
    messages = [
        {"role": "assistant", "content": "Hi! I'm your Career & Scholarship Advisor. Tell me about your background, interests, and goals to get started."},
        {"role": "user", "content": user_message}
    ]
    req = urllib.request.Request(
        f"{backend_url}/chat",
        data=json.dumps({"messages": messages, "turn": 0}).encode(),
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    response = urllib.request.urlopen(req)
    return json.loads(response.read().decode())

for query in ["hello", "china scholarship", "中国奖学金", "cv", "computer science career"]:
    print(f"\n=== {query} ===")
    try:
        result = chat(query)
        print(f"Status OK, is_final={result['is_final']}")
        print(result['reply'][:300])
    except Exception as e:
        print("Error:", e)
