import urllib.request
import json
import sys

sys.stdout.reconfigure(encoding='utf-8')

backend_url = "https://ferrari-paul-beijing-opposite.trycloudflare.com"

# Save a test chat
print("=== Saving test chat ===")
save_req = urllib.request.Request(
    f"{backend_url}/chats",
    data=json.dumps({
        "id": "test-chat-123",
        "title": "Test scholarship chat",
        "messages": [
            {"role": "assistant", "content": "Hi! How can I help?"},
            {"role": "user", "content": "I want a scholarship in China"},
            {"role": "assistant", "content": "Sure, here is some info..."}
        ],
        "turn": 1,
        "isFinal": False,
        "started": True
    }).encode(),
    headers={"Content-Type": "application/json"},
    method="POST"
)
try:
    response = urllib.request.urlopen(save_req)
    print("Save OK:", response.status, response.read().decode())
except Exception as e:
    print("Save failed:", e)

# List chats
print("\n=== Listing chats ===")
try:
    response = urllib.request.urlopen(f"{backend_url}/chats")
    data = json.loads(response.read().decode())
    print("List OK:", response.status)
    for chat in data.get("chats", []):
        print(f"- {chat['title']} (id: {chat['id']}, updatedAt: {chat['updatedAt']})")
except Exception as e:
    print("List failed:", e)

# Delete test chat
print("\n=== Deleting test chat ===")
delete_req = urllib.request.Request(
    f"{backend_url}/chats/test-chat-123",
    method="DELETE"
)
try:
    response = urllib.request.urlopen(delete_req)
    print("Delete OK:", response.status, response.read().decode())
except Exception as e:
    print("Delete failed:", e)
