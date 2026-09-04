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

messages = [
    {"role": "assistant", "content": "Hi! I'm your Career & Scholarship Advisor. Tell me about your background, interests, and goals to get started."},
]

print("=== User: make my CV ===")
messages.append({"role": "user", "content": "make my CV"})
result = chat(messages, 0)
print(f"is_final: {result['is_final']}")
print(result['reply'][:800])
print()
messages.append({"role": "assistant", "content": result['reply']})

print("=== User provides CV info ===")
cv_info = """Name: Aisha Khan
Email: aisha@example.com
Phone: +92-300-1234567
Education: BS Computer Science, FAST NUCES, GPA 3.8
Experience: 6 months internship at TechSol as frontend developer
Skills: React, Next.js, Python, TypeScript, Tailwind CSS
Projects: Built an AI career advisor web app, E-commerce website"""
messages.append({"role": "user", "content": cv_info})
result = chat(messages, 1)
print(f"is_final: {result['is_final']}")
print(result['reply'][:1500])
