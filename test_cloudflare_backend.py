import urllib.request

try:
    response = urllib.request.urlopen("https://ferrari-paul-beijing-opposite.trycloudflare.com/")
    print("Backend tunnel accessible:", response.status)
    print(response.read().decode())
except Exception as e:
    print("Backend tunnel check failed:", e)
