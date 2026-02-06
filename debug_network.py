import requests
import os

url = "https://huggingface.co/api/models/Helsinki-NLP/opus-mt-en-tr/revision/main"

print(f"Testing URL: {url}")
print(f"HF_TOKEN present: {'HF_TOKEN' in os.environ}")

try:
    resp = requests.get(url)
    print(f"Status Code: {resp.status_code}")
    print(f"Response: {resp.text[:200]}...")
except Exception as e:
    print(f"Requests Failed: {e}")
