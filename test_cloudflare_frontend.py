import urllib.request

try:
    response = urllib.request.urlopen("https://enclosure-affect-instrumentation-herein.trycloudflare.com/")
    print("Frontend tunnel accessible:", response.status)
    print(response.read().decode()[:500])
except Exception as e:
    print("Frontend tunnel check failed:", e)
