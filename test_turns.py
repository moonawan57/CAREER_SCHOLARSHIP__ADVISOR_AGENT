import urllib.request
import json

backend_url = "https://ferrari-paul-beijing-opposite.trycloudflare.com"

def test_turn(turn):
    messages = [
        {"role": "assistant", "content": "Hi! Tell me about your background."},
        {"role": "user", "content": "I am a CS student."}
    ]
    for i in range(turn):
        messages.append({"role": "assistant", "content": f"Question {i+1}?"})
        messages.append({"role": "user", "content": f"Answer {i+1}"})

    req = urllib.request.Request(
        f"{backend_url}/chat",
        data=json.dumps({"messages": messages, "turn": turn}).encode(),
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    try:
        response = urllib.request.urlopen(req)
        data = json.loads(response.read().decode())
        print(f"Turn {turn}: is_final={data['is_final']}")
        return data['is_final']
    except Exception as e:
        print(f"Turn {turn} failed: {e}")
        return None

print("Testing turn 17 (should be False):", test_turn(17))
print("Testing turn 18 (should be True):", test_turn(18))
