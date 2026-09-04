import urllib.request
import json

frontend_url = "https://annually-brave-symantec-parts.trycloudflare.com"
backend_url = "https://ferrari-paul-beijing-opposite.trycloudflare.com"

# Test frontend loads
print("Testing frontend...")
try:
    response = urllib.request.urlopen(frontend_url)
    print("Frontend OK:", response.status)
except Exception as e:
    print("Frontend failed:", e)

# Test chat from frontend origin
print("\nTesting chat...")
req = urllib.request.Request(
    f"{backend_url}/chat",
    data=json.dumps({
        "messages": [
            {"role": "assistant", "content": "Hi! Tell me about your background."},
            {"role": "user", "content": "I am 2 year student I want to know about bachelors scholarships available in china"}
        ],
        "turn": 0
    }).encode(),
    headers={
        "Content-Type": "application/json",
        "Origin": frontend_url,
    },
    method="POST"
)

try:
    response = urllib.request.urlopen(req)
    print("Chat OK:", response.status)
    print(response.read().decode())
except Exception as e:
    print("Chat failed:", e)
