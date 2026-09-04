import urllib.request
import json
import sys

sys.stdout.reconfigure(encoding='utf-8')

backend_url = "https://ferrari-paul-beijing-opposite.trycloudflare.com"

def save_chat(user_id, chat_id, title):
    req = urllib.request.Request(
        f"{backend_url}/chats",
        data=json.dumps({
            "userId": user_id,
            "id": chat_id,
            "title": title,
            "messages": [
                {"role": "assistant", "content": "Hi!"},
                {"role": "user", "content": f"Message from {user_id}"}
            ],
            "turn": 0,
            "isFinal": False,
            "started": True
        }).encode(),
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    response = urllib.request.urlopen(req)
    return response.status

def list_chats(user_id):
    response = urllib.request.urlopen(f"{backend_url}/chats?user_id={user_id}")
    return json.loads(response.read().decode())

user_a = "user-a-test"
user_b = "user-b-test"

print("=== Saving chats for two users ===")
print("User A save:", save_chat(user_a, "chat-a-1", "User A private chat"))
print("User B save:", save_chat(user_b, "chat-b-1", "User B private chat"))

print("\n=== User A sees ===")
for chat in list_chats(user_a)["chats"]:
    print(f"- {chat['title']}")

print("\n=== User B sees ===")
for chat in list_chats(user_b)["chats"]:
    print(f"- {chat['title']}")

# Cleanup
urllib.request.urlopen(urllib.request.Request(f"{backend_url}/chats/chat-a-1?user_id={user_a}", method="DELETE"))
urllib.request.urlopen(urllib.request.Request(f"{backend_url}/chats/chat-b-1?user_id={user_b}", method="DELETE"))
print("\nCleanup done")
