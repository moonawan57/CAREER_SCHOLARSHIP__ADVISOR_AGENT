import urllib.request
import io
import mimetypes

backend_url = "https://ferrari-paul-beijing-opposite.trycloudflare.com"

# Create a simple text file in memory
file_content = b"I am a high school student with GPA 3.8 interested in computer science scholarships."
boundary = "----WebKitFormBoundary7MA4YWxkTrZu0gW"

body = (
    f"--{boundary}\r\n"
    f'Content-Disposition: form-data; name="file"; filename="student.txt"\r\n'
    f"Content-Type: text/plain\r\n\r\n"
).encode() + file_content + f"\r\n--{boundary}--\r\n".encode()

req = urllib.request.Request(
    f"{backend_url}/upload",
    data=body,
    headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
    method="POST"
)

try:
    response = urllib.request.urlopen(req)
    print("Upload OK:", response.status)
    print(response.read().decode())
except Exception as e:
    print("Upload failed:", e)
