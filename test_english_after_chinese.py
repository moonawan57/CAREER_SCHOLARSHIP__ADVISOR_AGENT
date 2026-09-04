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
    {"role": "user", "content": "我想申请中国的计算机科学奖学金"},
    {"role": "assistant", "content": "- 确定目标奖学金..."},
    {"role": "user", "content": "can you tell me the scholarships available for bachelors in computer science?"}
]

print("=== English after Chinese ===")
result = chat(messages, 1)
print(f"is_final: {result['is_final']}")
print(f"reply: {result['reply'][:500]}")
