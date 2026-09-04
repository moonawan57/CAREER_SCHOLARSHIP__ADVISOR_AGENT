import urllib.request
import json

backend_url = "https://ferrari-paul-beijing-opposite.trycloudflare.com"

messages = [
    {"role": "assistant", "content": "Hi! Tell me about your background."},
    {"role": "user", "content": "I am a CS student."}
]

for turn in range(20):
    req = urllib.request.Request(
        f"{backend_url}/chat",
        data=json.dumps({"messages": messages, "turn": turn}).encode(),
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    try:
        response = urllib.request.urlopen(req)
        data = json.loads(response.read().decode())
        print(f"Turn {turn}: is_final={data['is_final']}, reply={data['reply'][:80]}...")
        messages.append({"role": "assistant", "content": data['reply']})
        if data['is_final']:
            print("FINAL RECOMMENDATION REACHED")
            break
        messages.append({"role": "user", "content": f"Answer {turn + 1}"})
    except Exception as e:
        print(f"Turn {turn} failed:", e)
        break
