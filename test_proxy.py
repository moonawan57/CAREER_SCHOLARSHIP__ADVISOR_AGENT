import requests

res = requests.post(
    "http://localhost:3000/chat",
    json={"messages": [{"role": "user", "content": "Hello"}], "turn": 1},
    timeout=120,
)
print("Status:", res.status_code)
print("Reply:", res.json().get("reply", "")[:200])
