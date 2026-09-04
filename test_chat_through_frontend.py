import urllib.request
import json

# Test backend through cloudflare backend tunnel
req1 = urllib.request.Request(
    "https://ferrari-paul-beijing-opposite.trycloudflare.com/chat",
    data=json.dumps({
        "messages": [
            {"role": "assistant", "content": "Hi! Tell me about your background."},
            {"role": "user", "content": "I am 2 year student I want to know about bachelors scholarships available in china"}
        ],
        "turn": 0
    }).encode(),
    headers={"Content-Type": "application/json", "Origin": "https://enclosure-affect-instrumentation-herein.trycloudflare.com"},
    method="POST"
)

try:
    response = urllib.request.urlopen(req1)
    print("Backend chat through tunnel:", response.status)
    print(response.read().decode()[:500])
except Exception as e:
    print("Backend chat failed:", e)

# Test CORS preflight
req2 = urllib.request.Request(
    "https://ferrari-paul-beijing-opposite.trycloudflare.com/chat",
    method="OPTIONS",
    headers={
        "Origin": "https://enclosure-affect-instrumentation-herein.trycloudflare.com",
        "Access-Control-Request-Method": "POST",
        "Access-Control-Request-Headers": "Content-Type"
    }
)

try:
    response = urllib.request.urlopen(req2)
    print("CORS preflight:", response.status)
    print(dict(response.headers))
except Exception as e:
    print("CORS preflight failed:", e)
