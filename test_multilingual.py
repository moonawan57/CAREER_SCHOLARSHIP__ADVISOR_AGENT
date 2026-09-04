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

print("=== Urdu (Roman): mujhe china mein scholarship chahiye ===")
result = chat("mujhe china mein scholarship chahiye computer science ke liye")
print(result['reply'][:600])
print(f"is_final: {result['is_final']}")
print()

print("=== Hindi: मुझे चीन में स्कॉलरशिप चाहिए ===")
result = chat("मुझे चीन में कंप्यूटर साइंस की स्कॉलरशिप चाहिए")
print(result['reply'][:600])
print(f"is_final: {result['is_final']}")
