import requests

# URL of the protected video
url = "http://localhost:8000/videos/intro.mp4"

# Access token from the cookie (e.g., after login)
access_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ1c2VyQGV4YW1wbGUuY29tIiwiZXhwIjoxNzg1NTYxNTU2fQ.PqnJ3XAs2lWPYP9n5RQVIEYbbb_q8NmlYEh4LNWbuts"

# Send GET request with cookie
response = requests.get(
    url,
    headers={
        "Cookie": f"access_token={access_token}"
    },
    stream=True  # Use stream=True to avoid downloading the whole file
)

# Check status
if response.status_code == 200:
    print("✅ Video is accessible and rendering (200 OK).")
    # Optional: check content type
    print("Content-Type:", response.headers.get('Content-Type'))
else:
    print(f"❌ Failed to load video. Status code: {response.status_code}")
    print("Response:", response.text)
