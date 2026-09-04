import urllib.request
import json

req = urllib.request.Request(
    "https://ferrari-paul-beijing-opposite.trycloudflare.com/chat",
    data=json.dumps({
        "messages": [
            {"role": "assistant", "content": "Hi! Tell me about your background."},
            {"role": "user", "content": "I am a CS student interested in AI."}
        ],
        "turn": 0
    }).encode(),
    headers={"Content-Type": "application/json"},
    method="POST"
)

try:
    response = urllib.request.urlopen(req)
    print("Chat endpoint accessible:", response.status)
    print(response.read().decode()[:500])
except Exception as e:
    print("Chat endpoint check failed:", e)
