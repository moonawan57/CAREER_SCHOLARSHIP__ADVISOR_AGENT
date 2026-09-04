import urllib.request
import json
import sys

sys.stdout.reconfigure(encoding='utf-8')

backend_url = "http://localhost:8000"

messages = [
    {"role": "assistant", "content": "Hi! I'm your Career & Scholarship Advisor. Tell me about your background, interests, and goals to get started."},
    {"role": "user", "content": "Make a CV for me. I am Ali, a computer science student with 3.5 GPA, skills in Python and React, one internship at a software house."}
]

req = urllib.request.Request(
    f"{backend_url}/chat",
    data=json.dumps({"messages": messages, "turn": 0}).encode(),
    headers={"Content-Type": "application/json"},
    method="POST"
)

try:
    response = urllib.request.urlopen(req, timeout=60)
    data = json.loads(response.read().decode())
    print("Status:", response.status)
    print("is_final:", data['is_final'])
    print("Reply:")
    print(data['reply'])
except urllib.error.HTTPError as e:
    print("HTTP Error:", e.code)
    print(e.read().decode())
except Exception as e:
    print("Error:", e)
