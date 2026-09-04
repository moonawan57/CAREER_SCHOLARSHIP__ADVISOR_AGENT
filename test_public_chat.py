import requests

url = "https://environmental-featured-eight-intelligent.trycloudflare.com/chat"
payload = {
    "messages": [
        {"role": "assistant", "content": "Hi! I'm your Career & Scholarship Advisor. Tell me about your background, interests, and goals to get started."},
        {"role": "user", "content": "hello"}
    ],
    "turn": 0
}

try:
    r = requests.post(url, json=payload, timeout=90)
    print("Status:", r.status_code)
    data = r.json()
    print("is_final:", data.get("is_final"))
    print("Reply:", data.get("reply", "")[:200])
except Exception as e:
    print("Error:", e)
