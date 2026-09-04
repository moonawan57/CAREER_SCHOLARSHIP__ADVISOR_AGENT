import urllib.request
import json
import sys

sys.stdout.reconfigure(encoding='utf-8')

backend_url = "https://ferrari-paul-beijing-opposite.trycloudflare.com"

req = urllib.request.Request(
    f"{backend_url}/chats",
    data=json.dumps({
        "userId": "user-a-test",
        "id": "chat-a-1",
        "title": "User A private chat",
        "messages": [
            {"role": "assistant", "content": "Hi!"},
            {"role": "user", "content": "Message from user A"}
        ],
        "turn": 0,
        "isFinal": False,
        "started": True
    }).encode(),
    headers={"Content-Type": "application/json"},
    method="POST"
)

try:
    response = urllib.request.urlopen(req)
    print("OK:", response.status, response.read().decode())
except urllib.error.HTTPError as e:
    print("Error:", e.code)
    print(e.read().decode())
