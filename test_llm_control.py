import urllib.request
import json
import sys

sys.stdout.reconfigure(encoding='utf-8')

backend_url = "https://ferrari-paul-beijing-opposite.trycloudflare.com"

def chat(messages, turn):
    req = urllib.request.Request(
        f"{backend_url}/chat",
        data=json.dumps({"messages": messages, "turn": turn}).encode(),
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    response = urllib.request.urlopen(req)
    return json.loads(response.read().decode())

# Test 1: Simple query should NOT be final
print("=== Test 1: Simple query ===")
messages = [
    {"role": "assistant", "content": "Hi! Tell me about your background."},
    {"role": "user", "content": "I want a scholarship abroad"}
]
result = chat(messages, 0)
print(f"is_final: {result['is_final']}")
print(f"reply preview: {result['reply'][:150]}...")
print()

# Test 2: After many answers, should be final
print("=== Test 2: Detailed profile (should trigger final) ===")
messages = [
    {"role": "assistant", "content": "Hi! Tell me about your background."},
    {"role": "user", "content": "I am a 3rd year Computer Science student in Pakistan. GPA 3.8. Interested in AI and Data Science. Want to do MS in USA or Germany. Have 2 research papers and 1 internship. Need scholarships."}
]
for turn in range(5):
    result = chat(messages, turn)
    print(f"Turn {turn}: is_final={result['is_final']}")
    messages.append({"role": "assistant", "content": result['reply']})
    if result['is_final']:
        print("Final recommendation reached!")
        print(result['reply'][:500])
        break
    messages.append({"role": "user", "content": "Tell me more based on what I shared."})
