import requests

urls = [
    ("frontend", "https://graham-dts-sara-wearing.trycloudflare.com"),
    ("backend", "https://environmental-featured-eight-intelligent.trycloudflare.com"),
]

for name, url in urls:
    try:
        r = requests.get(url, timeout=15)
        print(f"{name}: {r.status_code}")
    except Exception as e:
        print(f"{name}: FAIL - {e}")
